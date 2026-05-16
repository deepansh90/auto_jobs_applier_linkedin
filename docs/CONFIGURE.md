# Configure

**Fast path:** run the setup wizard — it writes `config/secrets.py` and `config/user.settings.json`.

```bash
./venv/bin/python -m applybot.setup
```

Then open **http://127.0.0.1:5000/** (or let the script open it), finish the steps, and run `./venv/bin/python runAiBot.py`.

---

**If you skip the wizard**, copy examples and edit by hand:

| Need | File |
|------|------|
| LinkedIn + AI keys | `cp config/secrets.example.py config/secrets.py` |
| Name, phone, address, EEO | `cp config/personals.example.py config/personals.py` |
| Resume path, LinkedIn URL, salary-related answers | `cp config/questions.example.py config/questions.py` |
| Salary, visa, notices | `cp config/answers.example.py config/answers.py` |
| Job titles & filters | `cp config/search.example.py config/search.py` |
| Limits & browser | `config/settings.py` (committed defaults; edit in place) |

`config/profile.json` is **created from your resume** on first bot run (or use `config/profile.example.json` as a template).

Optional keyword overrides: `config/custom_questions.example.py` → `custom_questions.py`.

---

## Config Map and Overlays

To maintain a predictable configuration experience, please note the following variable boundaries:
- `pause_before_submit`: Belongs in `config/questions.py` ONLY (avoid duplicating in settings.py).
- `offline_mode_strategy`: Belongs in `config/settings.py`.
- Search parameters (job titles, locations, filters): Belong in `config/search.py`.

### user.settings.json Overlay
The `user.settings.json` file safely overrides python configs at runtime. The currently supported keys and their target modules are:
- `search_terms`, `search_location`, `job_type`, `on_site`, `current_experience`, `experience_level` -> targets `config/search.py`
- `default_resume_path`, `desired_salary`, `years_of_experience` -> targets `config/questions.py`
- `follow_companies` -> targets `config/settings.py`

---

Next: **[RUN.md](RUN.md)** (login, logs, run the bot). Optional live LinkedIn regression (pytest, CSV + pre-submit dumps): **[RUN.md §7](RUN.md#7-live-e2e-optional-regression)**. URL filter codes: **[LINKEDIN_URL_REFERENCE.md](LINKEDIN_URL_REFERENCE.md)**.
