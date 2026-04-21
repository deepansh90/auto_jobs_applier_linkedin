"""
One-time resume auto-population.

On first run, if `config/profile.json` is missing and a resume PDF exists,
extract text and ask an AI provider to return a strict-JSON profile.
Falls back to regex extraction (email/phone/LinkedIn) when AI is unavailable.

Subsequent runs just load the on-disk `config/profile.json`.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from modules.helpers import print_lg


PROFILE_SCHEMA_HINT = """
Return ONLY valid JSON (no markdown, no prose) with this exact shape:
{
  "name": "<full legal name>",
  "first_name": "<first>",
  "last_name": "<last>",
  "email": "<email>",
  "phone": "<digits only, no country code>",
  "phone_country_code": "<like +1 or +91>",
  "location": {
    "city": "<city>",
    "state": "<state or province>",
    "country": "<country>",
    "street": "",
    "zipcode": ""
  },
  "linkedin_url": "<full https:// linkedin URL or empty>",
  "portfolio_url": "<full https:// URL or empty>",
  "summary": "<1-2 sentence professional summary>",
  "headline": "<one-line LinkedIn headline>",
  "skills": ["skill1", "skill2"],
  "years_of_experience": "<integer as string>",
  "recent_employer": "<most recent company name>"
}
Any field you cannot determine: use an empty string "" (or [] for skills).
"""


_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3}\)?[\s-]?)?\d{3}[\s-]?\d{4}")
_LINKEDIN_RE = re.compile(r"https?://(?:www\.)?linkedin\.com/in/[A-Za-z0-9_\-%.]+/?", re.I)


def _empty_profile() -> dict[str, Any]:
    return {
        "name": "", "first_name": "", "last_name": "",
        "email": "", "phone": "", "phone_country_code": "",
        "location": {"city": "", "state": "", "country": "", "street": "", "zipcode": ""},
        "linkedin_url": "", "portfolio_url": "",
        "summary": "", "headline": "",
        "skills": [], "years_of_experience": "", "recent_employer": "",
    }


def _extract_pdf_text(pdf_path: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # fallback for older installs
        except ImportError:
            print_lg("[autofill] pypdf not installed; cannot parse resume PDF.")
            return ""
    try:
        reader = PdfReader(pdf_path)
        parts = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(parts).strip()
    except Exception as e:
        print_lg(f"[autofill] Failed to read PDF '{pdf_path}': {e}")
        return ""


def _regex_fallback(text: str) -> dict[str, Any]:
    profile = _empty_profile()
    if not text:
        return profile
    m = _EMAIL_RE.search(text)
    if m:
        profile["email"] = m.group(0)
    m = _LINKEDIN_RE.search(text)
    if m:
        profile["linkedin_url"] = m.group(0).rstrip("/")
    m = _PHONE_RE.search(text)
    if m:
        digits = re.sub(r"\D", "", m.group(0))
        if len(digits) >= 10:
            profile["phone"] = digits[-10:]
            if len(digits) > 10:
                profile["phone_country_code"] = "+" + digits[:-10]
    for line in text.splitlines()[:5]:
        line = line.strip()
        if line and "@" not in line and not _PHONE_RE.search(line) and len(line.split()) <= 5 and any(c.isalpha() for c in line):
            profile["name"] = line
            parts = line.split()
            if parts:
                profile["first_name"] = parts[0]
                profile["last_name"] = parts[-1] if len(parts) > 1 else ""
            break
    return profile


def _ai_extract(text: str) -> dict[str, Any] | None:
    """Try Gemini -> OpenAI; return parsed dict or None."""
    prompt = f"Extract a structured profile from this resume text.\n{PROFILE_SCHEMA_HINT}\n\nResume text:\n{text[:8000]}"

    try:
        from config.secrets import llm_api_key
        if llm_api_key and "YOUR_API_KEY" not in str(llm_api_key):
            from modules.ai.geminiConnections import gemini_create_client, gemini_completion
            client = gemini_create_client()
            if client:
                result = gemini_completion(client, prompt, is_json=True)
                if isinstance(result, dict) and "error" not in result and result.get("name") is not None:
                    return result
                if isinstance(result, dict) and "error" in result:
                    print_lg(f"[autofill] Gemini returned error: {str(result.get('error'))[:200]}")
                    return None
                if isinstance(result, str):
                    try:
                        parsed = json.loads(result)
                        if isinstance(parsed, dict) and "error" not in parsed:
                            return parsed
                    except Exception:
                        pass
    except Exception as e:
        print_lg(f"[autofill] Gemini extraction failed: {e}")

    return None


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in (override or {}).items():
        if k == "location" and isinstance(v, dict):
            out["location"] = {**base.get("location", {}), **{kk: vv for kk, vv in v.items() if vv}}
        elif v not in (None, "", []):
            out[k] = v
    return out


def ensure_profile(config_dir: str, resume_path: str) -> dict[str, Any]:
    """
    Ensure config/profile.json exists. Returns the loaded profile.
    - If the file exists: load and return it (no re-extraction).
    - If missing: try AI extraction, fall back to regex, write to disk.
    """
    profile_path = os.path.join(config_dir, "profile.json")
    if os.path.exists(profile_path):
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print_lg(f"[autofill] Could not parse existing {profile_path}: {e}. Regenerating.")

    if not resume_path or not os.path.exists(resume_path):
        print_lg(f"[autofill] No resume at '{resume_path}'. Writing empty profile template.")
        profile = _empty_profile()
    else:
        print_lg(f"[autofill] Extracting profile from resume: {resume_path}")
        text = _extract_pdf_text(resume_path)
        profile = _empty_profile()
        if text:
            ai_profile = _ai_extract(text)
            if ai_profile:
                profile = _merge(profile, ai_profile)
                print_lg("[autofill] AI-based profile extraction succeeded.")
            else:
                regex_profile = _regex_fallback(text)
                profile = _merge(profile, regex_profile)
                print_lg("[autofill] AI unavailable; used regex fallback. Please review config/profile.json.")

    try:
        os.makedirs(config_dir, exist_ok=True)
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        print_lg(f"[autofill] Wrote {profile_path}. Edit it if any field is wrong.")
    except Exception as e:
        print_lg(f"[autofill] Failed to write profile.json: {e}")

    return profile
