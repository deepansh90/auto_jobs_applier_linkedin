# Run Guide

How to install dependencies and run the bot on your local machine.

## Prerequisites

- **macOS or Linux** (tested on macOS 15). Windows works but is not the primary target.
- **Python 3.10+** (3.13 recommended). Check with `python3 --version`.
- **Chromium** (recommended) or Google Chrome.
  - macOS: `brew install --cask chromium`
  - Linux: `sudo apt install chromium-browser` or your distro's equivalent.
- A valid LinkedIn account. Free accounts work; Premium is NOT required.

## 1. Clone and Install

```bash
git clone https://github.com/deepansh90/linkedin_easy_auto_applier_agent.git
cd linkedin_easy_auto_applier_agent

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## 2. Configure

Before the first run, follow [docs/CONFIGURE.md](CONFIGURE.md). Minimal setup:

```bash
cp /path/to/your_resume.pdf  resume.pdf
cp config/secrets.example.py config/secrets.py  && $EDITOR config/secrets.py
cp config/answers.example.py config/answers.py  && $EDITOR config/answers.py
```

Everything else (name, email, phone, location, LinkedIn, skills, years of experience, recent employer) is auto-populated from `resume.pdf` on first run.

## 3. First Run — Resume Extraction

The first time you run `python3 runAiBot.py`, it:

1. Reads `resume.pdf` using `pypdf`.
2. Asks the AI provider (Gemini by default) to return a JSON profile.
3. Writes `config/profile.json`.
4. Proceeds with the normal login + job search flow.

If the AI is unavailable, a regex fallback pulls email / phone / LinkedIn out of the resume and writes a partial `config/profile.json`. Open the file and fill in anything that's missing.

After the first run you can re-run the extraction by deleting `config/profile.json`.

## 4. First-Run Login

The first run opens a fresh Chromium window and navigates to LinkedIn. You have two options:

- **Automatic**: fill `username` + `password` in `config/secrets.py`. The bot logs you in.
- **Manual (recommended for accounts with 2FA or frequent CAPTCHAs)**: leave the bot at the login screen, log in yourself once. The persistent profile directory stores the session, so subsequent runs skip login entirely.

## 5. Run the Bot

```bash
python3 runAiBot.py
```

The bot will:

1. Open Chromium with your persistent profile.
2. Navigate to the LinkedIn Jobs search with your filters (watch for `f_EA=true` in the URL).
3. For each matching job: evaluate relevance (AI), click Easy Apply, answer questions, upload resume, submit.
4. Stop after `max_applied_jobs` successful submissions (see `config/settings.py`).

## 6. Monitoring a Run

While the bot is running, watch:

- **`logs/log.txt`** — full structured log. Grep for:
  - `f_EA=true` to confirm Easy Apply filter is applied.
  - `[DEBUG] Easy Apply modal opened` to confirm the critical path works.
  - `[DEBUG] First Next click succeeded` for each successful application.
  - `OFFLINE MODE` if the AI dispatcher fell back (not fatal; bot continues).
- **`logs/screenshots/`** — automatic screenshots on failure. Named by job ID and failure point.
- **`all excels/all_applied_applications_history.csv`** — row appended per successful application.
- **`all excels/all_failed_applications_history.csv`** — row per skipped/failed job with reason.

## 7. Stopping the Bot

- **Ctrl+C** in the terminal — graceful shutdown.
- Close the browser window — the next loop iteration detects `NoSuchWindowException` and the bot attempts one automatic re-init. If that fails it exits cleanly.

## 8. Smoke Test (Recommended First Run)

Before running with `max_applied_jobs = 50`, do a 3-job smoke test:

1. Set `max_applied_jobs = 3` in `config/settings.py`.
2. Set `run_in_background = False` so you can watch.
3. Run `python3 runAiBot.py`.
4. After 3 applications, inspect `logs/log.txt` and `all excels/all_applied_applications_history.csv`.
5. If everything looks right, bump `max_applied_jobs` to your target and run again.

## 9. Common Issues

See [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) for:

- "Next button not clicking" (fixed but troubleshooting steps documented).
- "All AI providers failed" (offline mode).
- Session / `InvalidSessionIdException` recovery.
- Chromium vs Chrome conflicts.

## 10. Updating

```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

Your `config/*.py` and `config/master_resume.json` are gitignored, so `git pull` never clobbers them.
