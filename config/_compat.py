"""
Compatibility shim: exposes legacy config names from the new two-file setup
(`profile.json` + `answers.py`).

This module is imported ONLY when `config/personals.py` or `config/questions.py`
is missing (i.e. new-user setup). If those legacy files exist, they take
precedence and this shim is unused.

Order of resolution for each legacy variable:
  1. explicit value in `config/answers.py` (user override)
  2. derived value from `config/profile.json` (AI-extracted)
  3. safe default ("" or 0 or False)
"""
from __future__ import annotations

import json
import os
from typing import Any


_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
_PROFILE_PATH = os.path.join(_CONFIG_DIR, "profile.json")


def _load_profile() -> dict[str, Any]:
    if not os.path.exists(_PROFILE_PATH):
        return {}
    try:
        with open(_PROFILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _load_answers() -> dict[str, Any]:
    try:
        from config import answers as _answers_mod  # type: ignore
    except Exception:
        return {}
    return {k: v for k, v in vars(_answers_mod).items() if not k.startswith("_")}


_profile = _load_profile()
_answers = _load_answers()
_location = _profile.get("location") or {}


def _pick(answers_key: str, profile_key: str | None = None, default: Any = "") -> Any:
    """Answers file wins, then profile, then default."""
    if answers_key in _answers and _answers[answers_key] not in (None, ""):
        return _answers[answers_key]
    if profile_key:
        val = _profile.get(profile_key)
        if val not in (None, "", []):
            return val
    return default


# ---------- legacy personals.py names ----------
first_name = _pick("first_name", "first_name", "")
middle_name = _pick("middle_name", None, "")
last_name = _pick("last_name", "last_name", "")
phone_number = _pick("phone_number", "phone", "")
current_city = _answers.get("current_city") or _location.get("city") or ""
street = _answers.get("street") or _location.get("street") or ""
state = _answers.get("state") or _location.get("state") or ""
zipcode = _answers.get("zipcode") or _location.get("zipcode") or ""
country = _answers.get("country") or _location.get("country") or ""
ethnicity = _answers.get("ethnicity", "")
gender = _answers.get("gender", "")
disability_status = _answers.get("disability_status", "")
veteran_status = _answers.get("veteran_status", "")


# ---------- legacy questions.py names ----------
default_resume_path = _answers.get("default_resume_path", "resume.pdf")
years_of_experience = _pick("years_of_experience", "years_of_experience", "0") or "0"
require_visa = _answers.get("require_visa", "No")
website = _answers.get("website") or _profile.get("portfolio_url") or ""
linkedIn = _answers.get("linkedIn") or _profile.get("linkedin_url") or ""
us_citizenship = _answers.get("us_citizenship", "Other")
desired_salary = _answers.get("desired_salary", 0)
current_ctc = _answers.get("current_ctc", 0)
notice_period = _answers.get("notice_period", 30)
linkedin_headline = _answers.get("linkedin_headline") or _profile.get("headline") or ""
linkedin_summary = _answers.get("linkedin_summary") or _profile.get("summary") or ""
cover_letter = _answers.get("cover_letter", "")
user_information_all = _answers.get("user_information_all") or _profile.get("summary") or ""
recent_employer = _answers.get("recent_employer") or _profile.get("recent_employer") or ""
confidence_level = str(_answers.get("confidence_level", "7") or "7")
pause_before_submit = bool(_answers.get("pause_before_submit", False))
pause_at_failed_question = bool(_answers.get("pause_at_failed_question", False))
overwrite_previous_answers = bool(_answers.get("overwrite_previous_answers", False))


# Names exported into `runAiBot` when legacy `personals.py` / `questions.py` are absent.
# Using explicit copies avoids `from _compat import *` overwriting a real `personals` import.
_PERSONALS_EXPORT = (
    "first_name",
    "middle_name",
    "last_name",
    "phone_number",
    "current_city",
    "street",
    "state",
    "zipcode",
    "country",
    "ethnicity",
    "gender",
    "disability_status",
    "veteran_status",
)
_QUESTIONS_EXPORT = (
    "default_resume_path",
    "years_of_experience",
    "require_visa",
    "website",
    "linkedIn",
    "us_citizenship",
    "desired_salary",
    "current_ctc",
    "notice_period",
    "linkedin_headline",
    "linkedin_summary",
    "cover_letter",
    "user_information_all",
    "recent_employer",
    "confidence_level",
    "pause_before_submit",
    "pause_at_failed_question",
    "overwrite_previous_answers",
)


def ensure_linked_in_url_global(g: dict) -> None:
    """
    ``from config.questions import *`` skips compat when questions.py exists; older or
    minimal copies may omit ``linkedIn`` (capital I) while ``__main__`` still references it.
    """
    if "linkedIn" in g:
        return
    li = ""
    try:
        from config import answers as _ans_mod  # type: ignore

        li = (
            str(getattr(_ans_mod, "linkedIn", "") or "")
            or str(getattr(_ans_mod, "linkedin", "") or "")
        ).strip()
    except Exception:
        pass
    if not li:
        prof = _load_profile()
        if prof:
            li = str(prof.get("linkedin_url") or "").strip()
    g["linkedIn"] = li


def apply_compat_to_run_globals(g: dict, need_personals: bool, need_questions: bool) -> None:
    """Populate `runAiBot` globals from this shim only for modules that failed to import."""
    src = globals()
    if need_personals:
        for name in _PERSONALS_EXPORT:
            g[name] = src[name]
    if need_questions:
        for name in _QUESTIONS_EXPORT:
            g[name] = src[name]


def synthesize_master_resume() -> dict[str, Any]:
    """Build a master_resume-compatible dict from profile.json (used by AI tailoring)."""
    if not _profile:
        return {}
    return {
        "personal_info": {
            "name": _profile.get("name", ""),
            "email": _profile.get("email", ""),
            "phone": _profile.get("phone", ""),
            "location": ", ".join([v for v in (_location.get("city"), _location.get("state"), _location.get("country")) if v]),
            "linkedin": _profile.get("linkedin_url", ""),
            "portfolio": _profile.get("portfolio_url", ""),
        },
        "summary_master": _profile.get("summary", ""),
        "skills": {"technologies": _profile.get("skills") or []},
    }
