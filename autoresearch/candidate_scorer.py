"""
candidate_scorer.py - THE ONE FILE THE AGENT EDITS.

Baseline = a behaviour-identical copy of applybot/job_matcher.score_job_match, with its magic
numbers lifted into constants so experiments are small, reviewable diffs.
(autoresearch/test_harness.py asserts this baseline matches production, so a
"baseline" run really is today's behaviour.)

Contract (do not change the signature):
    score_job_match(title, description, master_resume, config) -> int in [0, 100]

Rules for experiments (see program.md for the full list):
  * pure python stdlib only; deterministic; no I/O, no network, no LLM calls
  * never reference specific job ids / company names (prepare.py rejects that)
"""
import re

# ---- tunable constants (baseline values reproduce production) ---------------------------
TITLE_BONUS = 30            # points when a desired title matches the job title
SENIORITY_BONUS = 15        # fallback points for a seniority keyword when no title matched
SKILLS_MAX = 70             # max points from skill overlap
MIN_TITLE_WORD_LEN = 3      # title words must be longer than (MIN_TITLE_WORD_LEN - 1) chars
SENIORITY_KEYWORDS = ["lead", "staff", "principal", "senior", "manager", "architect", "head", "director", "vp"]


def score_job_match(title, description, master_resume, config=None):
    if not master_resume:
        return 50

    score = 0
    desc_low = description.lower()
    title_low = title.lower()

    p_info = master_resume.get("personal_info", {})
    desired_titles_raw = (
        p_info.get("title") or p_info.get("headline") or master_resume.get("title")
        or master_resume.get("summary_master", "")
    )

    desired_titles = []
    if desired_titles_raw:
        if isinstance(desired_titles_raw, list):
            desired_titles.extend(desired_titles_raw)
        else:
            desired_titles.extend([t.strip() for t in re.split(r"[,|/]", str(desired_titles_raw)) if t.strip()])

    if config:
        search_terms = config.get("search_terms", [])
        if isinstance(search_terms, list):
            desired_titles.extend(search_terms)

    for dt in desired_titles:
        dt_low = dt.lower()
        dt_words = [w for w in re.split(r"\s+", dt_low) if len(w) >= MIN_TITLE_WORD_LEN]
        if dt_words and all(word in title_low for word in dt_words):
            score += TITLE_BONUS
            break
        if dt_low in title_low:
            score += TITLE_BONUS
            break

    if score < TITLE_BONUS:
        if any(w in title_low for w in SENIORITY_KEYWORDS):
            score += SENIORITY_BONUS

    skills_raw = master_resume.get("skills", [])
    if isinstance(skills_raw, dict):
        skills = skills_raw.get("technologies") or skills_raw.get("skills") or []
    else:
        skills = skills_raw

    skills_matched = 0
    if skills:
        for skill in skills:
            skill_clean = str(skill).strip().lower()
            if not skill_clean:
                continue
            if re.search(r"\b" + re.escape(skill_clean) + r"\b", desc_low):
                skills_matched += 1
        score += int((skills_matched / len(skills)) * SKILLS_MAX)

    return min(100, score)
