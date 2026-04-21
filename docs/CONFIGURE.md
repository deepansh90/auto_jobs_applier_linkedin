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
| Salary, visa, notices | `cp config/answers.example.py config/answers.py` |
| Job titles & filters | `config/search.py` |
| Limits & browser | `config/settings.py` |

`config/profile.json` is **created from your resume** on first bot run (or use `config/profile.example.json` as a template).

Optional keyword overrides: `config/custom_questions.example.py` → `custom_questions.py`.

---

Next: **[RUN.md](RUN.md)** (login, logs). URL filter codes: **[LINKEDIN_URL_REFERENCE.md](LINKEDIN_URL_REFERENCE.md)**.
