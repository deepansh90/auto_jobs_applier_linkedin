import pytest
import os
import json
from applybot.job_matcher import score_job_match
from applybot.answer_router import get_answer_from_router, _match_keyword

def test_job_matcher_compatibility():
    # Test new format
    new_resume = {
        "personal_info": {"title": "Software Engineer, Python Developer"},
        "skills": {"technologies": ["Python", "Flask", "Selenium"]}
    }
    
    # Obvious match
    score = score_job_match("Senior Python Developer", "We need a Python developer with Selenium experience.", new_resume)
    assert score > 50 # Should get 30 for title + some for skills
    
    # Legacy format match
    legacy_resume = {
        "title": "Software Engineer",
        "skills": ["Python", "Flask"]
    }
    score = score_job_match("Software Engineer", "Python Flask expert", legacy_resume)
    assert score > 50

def test_answer_router_regex():
    assert _match_keyword("java", "Java developer") is not None
    assert _match_keyword("java", "javascript developer") is None
    assert _match_keyword("no", "Knowledge of python") is None
    assert _match_keyword("no", "answer is No") is not None

def test_job_matcher_no_resume():
    assert score_job_match("Title", "Desc", None) == 50
    assert score_job_match("Title", "Desc", {}) == 50

def test_job_matcher_seniority():
    # Title match gives 30 points
    resume = {"title": "Staff Engineer"}
    score = score_job_match("Senior Staff Engineer", "Description", resume)
    assert score == 30
