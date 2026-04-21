# Configuration Guide

What to edit before running `python3 runAiBot.py`. All files below live under [config/](../config/). Real files are gitignored so your PII never gets committed.

The flow is designed so that **you only need to provide a resume PDF**. The agent uses an AI provider to extract all personal details from it on first run. You only need to hand-edit a couple of rare values (salary, notice period, visa) that can't be inferred from a resume.

## Overview — 3 files total

| File | Required? | What it contains |
| ---- | --------- | ---------------- |
| `config/secrets.py` | Yes | LinkedIn credentials + AI API key(s) |
| `config/profile.json` | **Auto-generated** from your resume on first run. Edit only to fix AI mistakes. | Name, email, phone, location, LinkedIn URL, skills, years of experience, recent employer |
| `config/answers.py` | Recommended | Salary, notice period, visa, ethnicity, gender, and other rare questions |
| `config/custom_questions.py` | Optional | Per-company keyword overrides |

Plus search tuning in `config/search.py` and runtime flags in `config/settings.py`.

---

## 1. Credentials and API Keys — `config/secrets.py`

```bash
cp config/secrets.example.py config/secrets.py
```

Edit [config/secrets.py](../config/secrets.py):

- `username` / `password` — your LinkedIn login.
- `GEMINI_API_KEY` — get one free at https://aistudio.google.com/app/apikey. Recommended primary provider and required for resume auto-extraction.
- `OPENAI_API_KEY` — optional failover provider.
- `ai_provider` — `"gemini"` or `"openai"`.

If a key is left as a placeholder like `"<YOUR_*_API_KEY>"`, the dispatcher detects it and skips that provider.

---

## 2. Resume → `resume.pdf` (in project root)

Drop your resume at the project root (`./resume.pdf`) or point to another path via `answers.py → default_resume_path`.

On the first run, the agent:
1. Extracts text from the PDF via `pypdf`.
2. Asks Gemini to return a strict JSON profile.
3. Falls back to regex (email / phone / LinkedIn) if AI is unavailable.
4. Writes the result to [config/profile.json](../config/profile.json).

Open `config/profile.json` after the first run and correct anything the AI got wrong:

```json
{
  "name": "Jane Doe",
  "first_name": "Jane",
  "last_name": "Doe",
  "email": "jane@example.com",
  "phone": "5551234567",
  "phone_country_code": "+1",
  "location": {
    "city": "San Francisco",
    "state": "CA",
    "country": "USA",
    "street": "",
    "zipcode": ""
  },
  "linkedin_url": "https://www.linkedin.com/in/janedoe",
  "portfolio_url": "",
  "summary": "Senior engineer specializing in distributed systems.",
  "headline": "Senior Software Engineer",
  "skills": ["Python", "AWS", "Kubernetes"],
  "years_of_experience": "7",
  "recent_employer": "Acme Corp"
}
```

You can also skip auto-generation by creating this file manually using [config/profile.example.json](../config/profile.example.json).

---

## 3. Rare / Subjective Answers — `config/answers.py`

```bash
cp config/answers.example.py config/answers.py
```

Fill in what a resume does not tell the AI:

- `desired_salary`, `current_ctc`, `notice_period`
- `require_visa`, `us_citizenship`
- `ethnicity`, `gender`, `disability_status`, `veteran_status` (leave `""` to decline)
- `cover_letter` (free-text; AI will tailor per-job if left empty)
- Behaviour toggles: `pause_before_submit`, `pause_at_failed_question`, `overwrite_previous_answers`

Any field set here overrides the profile-derived value. See the file's comments for optional overrides like `first_name`, `recent_employer`, `linkedIn`.

---

## 4. Custom Question Answers — `config/custom_questions.py` (optional)

```bash
cp config/custom_questions.example.py config/custom_questions.py
```

Add case-insensitive keyword → answer mappings in [config/custom_questions.py](../config/custom_questions.py). Answer precedence:

`custom_answers (keyword match)` > `answers.py (explicit)` > `profile.json (AI-derived)` > `AI live answer` > `random/default`

Add company-specific compliance questions here as you encounter them in `logs/log.txt`.

---

## 5. Job Search Parameters — `config/search.py`

- `search_terms` — list of job titles, e.g. `["Staff Engineer", "Principal Architect"]`.
- `search_location` — e.g. `"Bengaluru, India"`, `"Remote"`, or `""`.
- `easy_apply_only = True` — recommended. Adds `&f_EA=true`.
- `sort_by`, `date_posted`, `job_type`, `on_site`, `experience_level` — encoded directly into the search URL (no dependency on LinkedIn's filter UI).

---

## 6. Runtime Settings — `config/settings.py`

- `max_applied_jobs` — stop after N successful Easy Apply submissions per run. Start with `3`.
- `use_url_filters_only = True` — recommended. Bypasses LinkedIn's filter UI entirely (resilient to layout changes).
- `use_chromium = True` — recommended. Install via `brew install --cask chromium`.
- `run_in_background = False` while debugging.

---

## Verification Checklist

Before your first run:

- [ ] `config/secrets.py` has real `username` / `password` and at least one real AI key.
- [ ] `resume.pdf` exists at the project root.
- [ ] `config/answers.py` has your salary / notice / visa values.
- [ ] `config/search.py` has your `search_terms` and `easy_apply_only = True`.
- [ ] Chromium is installed.

Then proceed to [RUN.md](RUN.md).

## Legacy `personals.py` / `questions.py` / `master_resume.json`

These legacy files are still supported — if they exist, the bot uses them directly and skips the new auto-extraction. If they are absent, the bot synthesizes their values from `profile.json` + `answers.py` through the compatibility shim in `config/_compat.py`. You do not need both.
