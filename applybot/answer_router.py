import json
import os
import re
from datetime import datetime
try:
    from config.personals import *
except ImportError: pass
try:
    from config.questions import *
except ImportError: pass

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

def get_answer_from_router(question_text, type="text"):
    """
    Returns the best answer for a given question based on precedence rules:
    1. Approved learned answers
    2. custom_questions.py
    3. Legacy answers (from config.answers if exists)
    4. Deterministic resume facts
    """
    q_low = str(question_text).lower().strip()
    
    # 1. Check learned answers (only if approved)
    learned = load_learned_answers()
    if q_low in learned and learned[q_low]["status"] == "approved":
        return learned[q_low]["answer"]
        
    # 2. Check custom_questions.py
    try:
        from config.custom_questions import custom_questions
        # custom_questions is often a dict or a list of dicts. 
        # If it's the legacy dict format:
        if isinstance(custom_questions, dict):
            for cq_key, val in custom_questions.items():
                if cq_key.lower() in q_low:
                    return str(val)
        # If it's the list of dicts format:
        elif isinstance(custom_questions, list):
            for cq in custom_questions:
                if cq.get("question", "").lower() in q_low:
                    return str(cq.get("answer"))
    except (ImportError, AttributeError):
        pass
        
    # 3. Check legacy answers
    try:
        from config.answers import answers as legacy_answers
        for q_key, val in legacy_answers.items():
            if q_key.lower() in q_low:
                return str(val)
    except (ImportError, AttributeError):
        pass
            
    # 4. Deterministic Resume Facts (common patterns)
    # Notice Period
    if any(w in q_low for w in ["notice period", "how soon", "start date"]):
        try:
            from config.questions import notice_period
            return str(notice_period)
        except ImportError: pass
        
    # Salary
    if any(w in q_low for w in ["salary", "compensation", "expected ctc"]):
        try:
            from config.questions import desired_salary
            return str(desired_salary)
        except ImportError: pass
        
    # Visa / Sponsorship
    if any(w in q_low for w in ["sponsor", "visa", "work auth", "authorized to work"]):
        try:
            from config.questions import require_visa
            return str(require_visa) # "Yes" or "No"
        except ImportError: pass
        
    # Years of experience
    if "years of experience" in q_low and "how many" in q_low:
        try:
            from config.questions import years_of_experience
            return str(years_of_experience)
        except ImportError: pass

    return None
