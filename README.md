# linkedin_easy_auto_applier_agent

An automated LinkedIn Easy Apply agent: searches for jobs matching your
preferences, answers Easy Apply questions using a multi-provider AI
dispatcher (Gemini / OpenAI), and submits applications on
your behalf.

Highlights:

- **Easy Apply filter** — search URLs always carry `f_EA=true`.
- **Multi-AI failover** — Gemini → OpenAI. Skips on auth
  errors, retries on quota errors.
- **Offline mode** — when all AI providers are unavailable, falls back
  to static config values instead of crashing.
- **Persistent session** — re-uses a logged-in Chrome profile to skip
  most CAPTCHAs.
- **Per-session logs + screenshots** — `logs/session_YYYYMMDD.log` and
  `logs/screenshots/` for easy debugging.

## Quick start

```bash
git clone https://github.com/deepansh90/auto_jobs_applier_linkedin.git
cd auto_jobs_applier_linkedin
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp /path/to/your_resume.pdf resume.pdf
cp config/secrets.example.py config/secrets.py && $EDITOR config/secrets.py
# optional: cp config/answers.example.py config/answers.py && $EDITOR config/answers.py

python3 runAiBot.py
```

On first run the agent extracts your name, email, phone, location,
LinkedIn URL, skills and experience from `resume.pdf` into
`config/profile.json` and uses that to answer form questions. Edit
`config/profile.json` afterwards to fix any extracted field.

## Security and privacy

- **Never commit** `config/secrets.py`, `config/profile.json`, `config/personals.py`, generated `logs/`, or your resume PDF. Copy from `*.example` templates only; those templates stay in git without real credentials.
- **LinkedIn password and API keys** live only on your machine (see `.gitignore`). Rotate keys if they were ever pasted into chat, logs, or a public repo.
- **AI providers** (Gemini, OpenAI) receive prompts that can include résumé snippets and form questions—only enable AI if you accept that policy.
- **Before `git push`**: run `git status` and confirm you are not adding ignored personal files. Optionally scan for accidental secrets:

  ```bash
  git grep -nE 'AIza[0-9A-Za-z_-]{20,}|sk-[a-zA-Z0-9]{20,}|password\s*=' -- . ':!*.example.py' ':!**/archive_test_profile/**' || true
  ```

  Replace any real keys in tracked files with placeholders before pushing.

## Documentation

- [docs/CONFIGURE.md](docs/CONFIGURE.md) — what to edit before running.
- [docs/RUN.md](docs/RUN.md) — install + run.
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) — common issues.
- [docs/LINKEDIN_URL_REFERENCE.md](docs/LINKEDIN_URL_REFERENCE.md) —
  which LinkedIn search URL params are respected.

## Terms

Automated interaction with LinkedIn may violate their Terms of Service.
Use at your own risk on your own account.

## License

MIT — see [LICENSE](LICENSE).
