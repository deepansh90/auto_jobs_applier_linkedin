"""
Pre-submit audit: compare Easy Apply answers to profile.json; optional custom_answers fixes.

Screenshots and JSONL audit records are triggered from applybot.__main__ (see env vars there).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_profile_truth(root: Path | None = None) -> dict[str, Any] | None:
    """Load config/profile.json if present; returns a dict or None."""
    base = root or repo_root()
    path = base / "config" / "profile.json"
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _norm_question_rows(questions_list: Iterable[Any]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for item in questions_list or ():
        if not item:
            continue
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            label, value = str(item[0]), str(item[1])
            rows.append((label, value))
    return rows


def _skill_tail_from_years_label(label_lower: str) -> str | None:
    """Heuristic: skill token after ' in ' for years-style questions."""
    if "year" not in label_lower:
        return None
    if " in " not in label_lower:
        return None
    tail = label_lower.rsplit(" in ", 1)[-1].strip()
    tail = re.sub(r"[^a-z0-9+#.\s-]+", " ", tail, flags=re.I)
    tail = tail.split()[0] if tail.split() else ""
    return tail or None


def _profile_skill_tokens(profile: dict[str, Any]) -> set[str]:
    skills = profile.get("skills") or []
    out: set[str] = set()
    if isinstance(skills, list):
        for s in skills:
            if isinstance(s, str) and s.strip():
                out.add(s.strip().lower())
    return out


def _digits_only(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _parse_int_years(s: str | None) -> int | None:
    if not s:
        return None
    s = str(s).strip()
    if s.isdigit():
        return int(s)
    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else None


def _skip_email_value_audit(label: str, value: str) -> bool:
    """Avoid false positives: Yes/No answers, polluted labels, non-email-shaped values."""
    # Patch 3: Skip garbage labels (e.g., School dropdown with thousands of university names)
    if len(label) > 300:
        return True
    val_st = (value or "").strip()
    low = val_st.lower()
    # Patch 3: Skip common bot placeholder / default values
    if low in ("yes", "no", "y", "n", "", "unknown", "select an option", "true", "false"):
        return True
    if "[" in label or "select an option" in label.lower():
        return True
    if "@" not in val_st:
        return True
    return False


def _skip_phone_value_audit(value: str) -> bool:
    low = (value or "").strip().lower()
    if low in ("yes", "no", "y", "n", ""):
        return True
    return False


@dataclass
class AuditResult:
    mismatches: list[dict[str, Any]] = field(default_factory=list)
    has_high_severity: bool = False
    """Suggested (keyword, value) pairs for custom_answers — value is plain text for the form."""
    suggested_fixes: list[tuple[str, str]] = field(default_factory=list)


def audit_questions_list(
    questions_list: Iterable[Any],
    profile_truth: dict[str, Any] | None,
    default_years: str,
) -> AuditResult:
    """
    Compare filled answers (label, value) to profile.json years / skills.

    Conservative: HIGH severity only when a skill-specific years field disagrees
    with profile ``years_of_experience`` and the skill appears in profile skills.
    """
    out = AuditResult()
    profile_years = None
    if profile_truth:
        profile_years = _parse_int_years(profile_truth.get("years_of_experience"))
    fallback_years = _parse_int_years(default_years)
    ref_years = profile_years if profile_years is not None else fallback_years

    skill_tokens = _profile_skill_tokens(profile_truth) if profile_truth else set()

    for label, value in _norm_question_rows(questions_list):
        label_l = label.lower()
        val_st = value.strip()
        if profile_truth and val_st:
            email = (profile_truth.get("email") or "").strip()
            if (
                email
                and "email" in label_l
                and not _skip_email_value_audit(label, value)
                and email.lower() not in val_st.lower()
            ):
                out.mismatches.append(
                    {
                        "label": label,
                        "value": value,
                        "kind": "email",
                        "severity": "low",
                    }
                )
            phone = (profile_truth.get("phone") or "").strip()
            if phone and not _skip_phone_value_audit(value):
                pd = _digits_only(phone)
                vd = _digits_only(val_st)
                if (
                    len(pd) >= 7
                    and ("phone" in label_l or "mobile" in label_l)
                    and vd
                    and pd not in vd
                ):
                    out.mismatches.append(
                        {
                            "label": label,
                            "value": value,
                            "kind": "phone",
                            "severity": "low",
                        }
                    )
            fn = (profile_truth.get("first_name") or "").strip()
            if fn and "first name" in label_l and fn.lower() not in val_st.lower():
                out.mismatches.append(
                    {
                        "label": label,
                        "value": value,
                        "kind": "first_name",
                        "severity": "low",
                    }
                )

        if not val_st or not ref_years:
            continue
        if not val_st.replace(".", "", 1).isdigit():
            continue
        try:
            v_int = int(float(val_st)) if "." in val_st else int(val_st)
        except ValueError:
            continue

        skill = _skill_tail_from_years_label(label_l)
        if not skill:
            continue

        matched_skill = skill in skill_tokens or any(
            skill in t or t in skill for t in skill_tokens
        )
        if not matched_skill or not profile_truth:
            continue

        if v_int != ref_years:
            out.has_high_severity = True
            out.mismatches.append(
                {
                    "label": label,
                    "value": value,
                    "expected_years": ref_years,
                    "skill": skill,
                    "severity": "high",
                }
            )
            out.suggested_fixes.append((skill, str(ref_years)))

    dedup: dict[str, tuple[str, str]] = {}
    for k, v in out.suggested_fixes:
        dedup[k.lower()] = (k, v)
    out.suggested_fixes = list(dedup.values())

    return out


def _escape_py_doublequoted(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def append_custom_answer_fix(config_path: str | Path, keyword: str, value: str) -> bool:
    """
    Merge one entry into ``custom_answers`` in config/custom_questions.py.
    Returns True if the file was written.
    """
    path = Path(config_path)
    if not path.is_file():
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    if "custom_answers = {" not in content:
        return False

    kw = keyword.strip()
    if not kw:
        return False
    esc_val = _escape_py_doublequoted(value)
    new_line = f'    "{kw}": "{esc_val}",'

    # Replace existing key line (case-sensitive key match as stored)
    pattern = re.compile(
        rf'^(\s*)"{re.escape(kw)}":\s*".*",?\s*$',
        re.MULTILINE | re.IGNORECASE,
    )
    if pattern.search(content):
        content_new = pattern.sub(new_line, content, count=1)
        if content_new != content:
            path.write_text(content_new, encoding="utf-8")
            return True
        return False

    last = content.rfind("}")
    if last == -1:
        return False
    insert = content[:last].rstrip() + "\n" + new_line + "\n" + content[last:]
    path.write_text(insert, encoding="utf-8")
    return True


def append_pre_submit_audit_jsonl(
    audit_path: str | Path,
    job_id: str,
    job_link: str,
    payload: dict[str, Any],
) -> None:
    p = Path(audit_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "job_id": job_id,
        "job_link": job_link,
        **payload,
    }
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def save_pre_submit_screenshots(
    driver: WebDriver,
    modal: WebElement | None,
    job_id: str,
    root: Path | None = None,
) -> list[str]:
    """
    Full-page screenshot plus optional modal element screenshot.
    Returns list of relative paths written.
    """
    base = root or repo_root()
    out_dir = base / "history" / "screenshots" / "pre_submit"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_job = str(job_id).replace(":", ".")
    written: list[str] = []

    full_path = out_dir / f"pre_submit_full_{safe_job}_{ts}.png"
    try:
        driver.save_screenshot(str(full_path))
        written.append(str(full_path.relative_to(base)))
    except Exception:
        pass

    if modal is not None:
        modal_path = out_dir / f"pre_submit_modal_{safe_job}_{ts}.png"
        try:
            modal.screenshot(str(modal_path))
            written.append(str(modal_path.relative_to(base)))
        except Exception:
            pass
    return written


def env_truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")
