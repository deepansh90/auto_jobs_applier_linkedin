import json
import os
import re
from datetime import datetime

# Path for the learned answers store
LEARNED_ANSWERS_PATH = os.path.join("config", "learned_answers.json")

def load_learned_answers():
    if os.path.exists(LEARNED_ANSWERS_PATH):
        try:
            with open(LEARNED_ANSWERS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_learned_answer(question, answer, status="pending_review"):
    answers = load_learned_answers()
    # Normalize question for matching
    q_norm = str(question).lower().strip()
    answers[q_norm] = {
        "answer": str(answer),
        "status": status,
        "last_updated": datetime.now().isoformat()
    }
    os.makedirs("config", exist_ok=True)
    with open(LEARNED_ANSWERS_PATH, "w", encoding="utf-8") as f:
        json.dump(answers, f, indent=4)

def _match_keyword(keyword, text):
    """Case-insensitive word-boundary match."""
    k = str(keyword).lower().strip()
    t = str(text).lower().strip()
    if not k or not t: return False
    return re.search(r'\b' + re.escape(k) + r'\b', t)



def get_answer_from_router(question_text, type="text"):
    """
    Returns the best answer for a given question based on precedence rules:
    1. Approved learned answers
    2. custom_questions.py (custom_answers or custom_questions)
    3. Legacy config variables (personals, questions)
    4. Deterministic resume facts
    """
    q_low = str(question_text).lower().strip()
    
    # 1. Check learned answers (only if approved)
    learned = load_learned_answers()
    if q_low in learned and learned[q_low]["status"] == "approved":
        return learned[q_low]["answer"]
        
    # 2. Check custom_questions.py
    try:
        from config import custom_questions as cq_mod
        
        # Try custom_answers (dict format)
        custom_answers = getattr(cq_mod, "custom_answers", None)
        if isinstance(custom_answers, dict):
            for cq_key, val in custom_answers.items():
                if _match_keyword(cq_key, q_low):
                    return str(val)
        
        # Fallback to custom_questions (list of dicts or dict)
        custom_questions = getattr(cq_mod, "custom_questions", None)
        if isinstance(custom_questions, dict):
            for cq_key, val in custom_questions.items():
                if _match_keyword(cq_key, q_low):
                    return str(val)
        elif isinstance(custom_questions, list):
            for cq in custom_questions:
                if _match_keyword(cq.get("question", ""), q_low):
                    return str(cq.get("answer"))
    except (ImportError, AttributeError):
        pass
        
    # 3. Check legacy config variables directly (avoiding answers dict as it is rarely used)
    # We use _compat style lookup for core fields
    
    # Notice Period
    if any(_match_keyword(w, q_low) for w in ["notice period", "notice", "start date"]):
        try:
            from config.questions import notice_period
            return str(notice_period)
        except ImportError: pass
        
    # Salary
    if any(_match_keyword(w, q_low) for w in ["salary", "compensation", "expected ctc", "remuneration"]):
        try:
            from config.questions import desired_salary
            return str(desired_salary)
        except ImportError: pass
        
    # Visa / Sponsorship
    if any(_match_keyword(w, q_low) for w in ["sponsor", "visa", "work auth", "authorized", "citizenship"]):
        try:
            from config.questions import require_visa
            return str(require_visa)
        except ImportError: pass
        
    # Years of experience
    if _match_keyword("years", q_low) and any(_match_keyword(w, q_low) for w in ["experience", "relevant"]):
        try:
            from config.questions import years_of_experience
            return str(years_of_experience)
        except ImportError: pass
        
    # Website / Portfolio
    if any(_match_keyword(w, q_low) for w in ["website", "portfolio", "blog", "link"]):
        try:
            from config.questions import website
            if website: return str(website)
        except ImportError: pass

    # LinkedIn
    if _match_keyword("linkedin", q_low):
        try:
            from config.questions import linkedIn
            if linkedIn: return str(linkedIn)
        except ImportError: pass

    return None
