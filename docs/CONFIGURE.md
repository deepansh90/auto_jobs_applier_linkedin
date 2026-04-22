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
| Job titles & filters | `config/search.py` (committed defaults; edit in place) |
| Limits & browser | `config/settings.py` (committed defaults; edit in place) |

`config/profile.json` is **created from your resume** on first bot run (or use `config/profile.example.json` as a template).

Optional keyword overrides: `config/custom_questions.example.py` → `custom_questions.py`.

---

Next: **[RUN.md](RUN.md)** (login, logs, run the bot). Optional live LinkedIn regression (pytest, CSV + pre-submit dumps): **[RUN.md §7](RUN.md#7-live-e2e-optional-regression)**. URL filter codes: **[LINKEDIN_URL_REFERENCE.md](LINKEDIN_URL_REFERENCE.md)**.
