import os
import json
import re
from datetime import datetime

def check_hard_filters(title, company, description, config):
    """
    Applies hard filters to immediately disqualify a job based on deterministic rules.
    Returns: (skip: bool, skipReason: str, skipMessage: str)
    """
    desc_low = description.lower()
    
    # 1. Blocked Companies (Case-insensitive exact/partial match)
    blacklisted = config.get("blacklisted_companies", [])
    for bl_company in blacklisted:
        if bl_company.lower() in company.lower():
            return True, "Blacklisted Company", f'Company "{company}" is blacklisted. ({bl_company})'

    # 2. Blocked Titles / Bad Words in Title
    bad_words = config.get("bad_words", [])
    title_low = title.lower()
    for word in bad_words:
        w = (word or "").strip()
        if not w:
            continue
        wl = w.lower()
        if wl in title_low:
             return True, "Bad Word in Title", f'Title "{title}" contains bad word "{word}".'
        
        # 3. Bad words in Description
        try:
            if re.match(r"^[^\w]", wl):
                pat = re.compile(r"(?<!\w)" + re.escape(wl) + r"(?!\w)")
            else:
                pat = re.compile(r"\b" + re.escape(wl) + r"\b")
        except re.error:
            continue
        if pat.search(desc_low):
            return True, "Bad Word in Description", f'Contains bad word "{word}".'

    # 4. Security Clearance
    if not config.get("security_clearance", False):
        if any(w in desc_low for w in ['polygraph', 'clearance', 'secret']):
            return True, "Security Clearance Required", 'Found "Clearance", "Secret", or "Polygraph" in description.'

    return False, "", ""

def score_job_match(title, description, master_resume, config=None):
    """
    Computes a deterministic match score based on skills, title matches, and seniority.
    Returns a score between 0 and 100.
    """
    if not master_resume:
        return 50 # Default middle score if no resume facts
        
    score = 0
    desc_low = description.lower()
    title_low = title.lower()
    
    # Title matching: Use headline/title from resume AND search terms from config
    p_info = master_resume.get("personal_info", {})
    desired_titles_raw = p_info.get("title") or p_info.get("headline") or master_resume.get("title") or master_resume.get("summary_master", "")
    
    desired_titles = []
    if desired_titles_raw:
        if isinstance(desired_titles_raw, list):
            desired_titles.extend(desired_titles_raw)
        else:
            # Split on comma, pipe, or slash
            desired_titles.extend([t.strip() for t in re.split(r'[,|/]', str(desired_titles_raw)) if t.strip()])
    
    # Add search terms from config as potential matches
    if config:
        search_terms = config.get("search_terms", [])
        if isinstance(search_terms, list):
            desired_titles.extend(search_terms)

    for dt in desired_titles:
        dt_low = dt.lower()
        # Flexible match: check if all words in dt are present in title_low
        dt_words = [w for w in re.split(r'\s+', dt_low) if len(w) > 2]
        if dt_words and all(word in title_low for word in dt_words):
            score += 30
            break
        # Also keep the exact substring match for short titles
        if dt_low in title_low:
            score += 30
            break
            
    # Seniority/Role Keyword match (bonus points if not already capped)
    if score < 30:
        seniority_keywords = ["lead", "staff", "principal", "senior", "manager", "architect", "head", "director", "vp"]
        if any(w in title_low for w in seniority_keywords):
            score += 15
            
    # Skill matching
    # New format: master_resume["skills"]["technologies"] (list)
    # Legacy format: master_resume["skills"] (list)
    skills_raw = master_resume.get("skills", [])
    if isinstance(skills_raw, dict):
        skills = skills_raw.get("technologies") or skills_raw.get("skills") or []
    else:
        skills = skills_raw
        
    skills_matched = 0
    if skills:
        for skill in skills:
            skill_clean = str(skill).strip().lower()
            if not skill_clean: continue
            # Look for the exact skill as a whole word
            if re.search(r"\b" + re.escape(skill_clean) + r"\b", desc_low):
                skills_matched += 1
            
        # Max 70 points from skills (total 100 with title)
        skill_ratio = skills_matched / len(skills)
        score += int(skill_ratio * 70)
        
    return min(100, score)

def evaluate_job(job_id, title, company, description, config, master_resume=None):
    """
    Evaluates a job against deterministic hard filters and basic scoring.
    Logs the decision to JSONL.
    Returns a dict with the decision.
    """
    decision = {
        "timestamp": datetime.now().isoformat(),
        "job_id": job_id,
        "title": title,
        "company": company,
        "skip": False,
        "skip_reason": None,
        "deterministic_score": 0,
        "requires_ai": True
    }
    
    # 1. Check Hard Filters
    skip, reason, msg = check_hard_filters(title, company, description, config)
    if skip:
        decision["skip"] = True
        decision["skip_reason"] = reason
        decision["skip_message"] = msg
        decision["requires_ai"] = False
        _log_decision(decision)
        return decision
        
    # 2. Deterministic Scoring
    score = score_job_match(title, description, master_resume, config)
    decision["deterministic_score"] = score
    
    # 3. Apply Thresholds
    threshold = config.get("min_job_relevance_score", 50)
    if score >= 75:
        # Excellent match deterministically, bypass AI if needed
        decision["skip"] = False
        decision["skip_reason"] = "Deterministic Auto-Approve"
        decision["requires_ai"] = False
    elif score < threshold:
        # Terrible match deterministically
        decision["skip"] = True
        decision["skip_reason"] = f"Deterministic Score Too Low ({score} < {threshold})"
        decision["skip_message"] = f"Deterministic match score is very low ({score})."
        decision["requires_ai"] = False
    else:
        # Borderline match, requires AI explanation
        decision["requires_ai"] = True
        
    _log_decision(decision)
    return decision

def _log_decision(decision):
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "job_match_decisions.jsonl")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(decision) + "\n")
    except Exception:
        pass
