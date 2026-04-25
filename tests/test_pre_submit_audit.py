"""Unit tests for pre-submit audit and custom_answers merge (no LinkedIn)."""

from __future__ import annotations

import json
from pathlib import Path

from applybot.pre_submit_verify import (
    append_custom_answer_fix,
    audit_questions_list,
    load_profile_truth,
)


def test_audit_skill_years_mismatch_detected() -> None:
    profile = {
        "years_of_experience": "5",
        "skills": ["Java", "Python"],
    }
    rows = [
        ("How many years of experience do you have in Java?", "3"),
    ]
    r = audit_questions_list(rows, profile, default_years="0")
    assert r.has_high_severity
    assert len(r.mismatches) == 1
    assert r.mismatches[0]["skill"] == "java"
    assert r.mismatches[0]["expected_years"] == 5
    assert ("java", "5") in r.suggested_fixes


def test_audit_matching_years_no_mismatch() -> None:
    profile = {
        "years_of_experience": "5",
        "skills": ["java"],
    }
    rows = [("How many years of experience do you have in Java?", "5")]
    r = audit_questions_list(rows, profile, default_years="0")
    assert not r.has_high_severity
    assert r.mismatches == []


def test_audit_no_profile_skips_skill_match() -> None:
    rows = [("How many years of experience do you have in Java?", "99")]
    r = audit_questions_list(rows, None, default_years="5")
    assert not r.mismatches


def test_audit_email_guard_yes_no_skipped() -> None:
    profile = {
        "years_of_experience": "5",
        "skills": ["java"],
        "email": "me@example.com",
    }
    rows = [
        ('Email address [  "Select an option", "me@example.com", ]', "Yes"),
        ("How many years of experience do you have in Java?", "5"),
    ]
    r = audit_questions_list(rows, profile, default_years="0")
    assert not any(m.get("kind") == "email" for m in r.mismatches)


def test_audit_email_light_mismatch_low_only() -> None:
    profile = {
        "years_of_experience": "5",
        "skills": ["java"],
        "email": "me@example.com",
    }
    rows = [
        ("Email address", "wrong@other.com"),
        ("How many years of experience do you have in Java?", "5"),
    ]
    r = audit_questions_list(rows, profile, default_years="0")
    assert not r.has_high_severity
    assert any(m.get("kind") == "email" for m in r.mismatches)


def test_audit_fallback_years_when_profile_missing_years() -> None:
    profile = {"skills": ["java"]}
    rows = [("How many years of experience do you have in Java?", "2")]
    r = audit_questions_list(rows, profile, default_years="7")
    assert r.has_high_severity
    assert r.mismatches[0]["expected_years"] == 7


def test_load_profile_truth_missing_returns_none(tmp_path: Path) -> None:
    assert load_profile_truth(tmp_path) is None


def test_load_profile_truth_reads_json(tmp_path: Path) -> None:
    cfg = tmp_path / "config"
    cfg.mkdir()
    data = {"years_of_experience": "3", "skills": ["Go"]}
    (cfg / "profile.json").write_text(json.dumps(data), encoding="utf-8")
    loaded = load_profile_truth(tmp_path)
    assert loaded == data


_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_append_custom_answer_fix_inserts_line(tmp_path: Path) -> None:
    src = _REPO_ROOT / "config" / "custom_questions.example.py"
    dst = tmp_path / "custom_questions.py"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    assert append_custom_answer_fix(dst, "java", "8")
    text = dst.read_text(encoding="utf-8")
    assert '"java": "8"' in text


def test_append_custom_answer_fix_replaces_existing(tmp_path: Path) -> None:
    src = _REPO_ROOT / "config" / "custom_questions.example.py"
    dst = tmp_path / "custom_questions.py"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    assert append_custom_answer_fix(dst, "python", "99")
    text = dst.read_text(encoding="utf-8")
    assert '"python": "99"' in text
    assert text.count('"python":') == 1
