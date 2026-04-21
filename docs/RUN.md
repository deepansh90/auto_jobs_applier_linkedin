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
```

On macOS, `python3` after `source venv/bin/activate` can still point at Homebrew instead of the venv. Prefer the venv interpreter explicitly (also avoids a missing `pip` on `PATH`):

```bash
./venv/bin/python -m pip install -U pip
./venv/bin/python -m pip install -r requirements.txt
```

Windows (after `python -m venv venv`):

```bash
venv\Scripts\python.exe -m pip install -U pip
venv\Scripts\python.exe -m pip install -r requirements.txt
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

The first time you run `./venv/bin/python runAiBot.py` (or `python3 runAiBot.py` if your shell’s `python3` is the venv), it:

1. Reads `resume.pdf` using `pypdf`.
2. Asks the AI provider (Gemini by default) to return a JSON profile.
3. Writes `config/profile.json`.
4. Proceeds with the normal login + job search flow.

If the AI is unavailable, a regex fallback pulls email / phone / LinkedIn out of the resume and writes a partial `config/profile.json`. Open the file and fill in anything that's missing.

After the first run you can re-run the extraction by deleting `config/profile.json`.

## 4. First-Run Login

`username` / `password` are read from `config/secrets.py` **when the Python process starts**. If you used the setup wizard, save, then **start** `./venv/bin/python runAiBot.py` again so a new process imports the file.

The first run opens a fresh Chromium window and navigates to LinkedIn. You have two options:

- **Automatic**: fill `username` + `password` in `config/secrets.py`. The bot fills LinkedIn’s **email + password** form and clicks **Sign in**. It does **not** drive Google’s **“Continue as …”** button—if you only see Google SSO, use **Sign in with email** on LinkedIn (or log in manually once).
- **Manual (recommended for accounts with 2FA or frequent CAPTCHAs)**: finish any checkpoint in the open browser window. The bot waits up to **3 minutes** for a successful URL (`/feed`, `/jobs`, `/mynetwork`, or your `/in/` profile). If it used to time out while you were already logged in on **Jobs**, that path is now recognized too.
- **Still stuck?** Wrong credentials in `config/secrets.py`, CAPTCHA, or LinkedIn security prompts—the terminal will ask you to complete login manually after the wait.

## 5. CLI: onboarding vs Easy Apply

| Goal | Command |
|------|---------|
| First-time **onboarding** (web form for LinkedIn + resume + search prefs) | `./venv/bin/python -m applybot.setup` — your browser should open **http://127.0.0.1:5000/**; if not, open it manually. Use `--no-browser` or `APPLYBOT_SETUP_NO_BROWSER=1` to skip auto-open (SSH/CI). |
| See setup CLI flags | `./venv/bin/python -m applybot.setup --help` |
| Check setup wiring without starting the server | `./venv/bin/python -m applybot.setup --dry-run` |
| **Easy Apply** job run (browser automation) | `./venv/bin/python runAiBot.py` |
| Bot CLI help (no browser) | `./venv/bin/python runAiBot.py --help` |
| Validate all `config/*.py` and exit | `./venv/bin/python runAiBot.py --validate-config` |
| **Onboarding wizard** HTTP checks (CI-safe) | `./venv/bin/python -m pytest tests/e2e/test_onboarding_setup.py -v` |

After **Complete Setup**, copy **`./venv/bin/python runAiBot.py`** from the success screen and run it in a terminal at the repo root (no in-page LinkedIn launch).

`--validate-config` requires a real `config/secrets.py` (same as a normal run). In CI, only `--help` / `--dry-run` are guaranteed without secrets; see `tests/test_cli.py` (run with `./venv/bin/python -m pytest tests/test_cli.py -v` from the repo root).

### Live E2E (at least 3 Easy Apply rows in CSV)

Opt-in only (`RUN_LINKEDIN_E2E=1`). Runs the real browser against LinkedIn and asserts the applications CSV grew by at least **3** rows (configurable with `LINKEDIN_E2E_MIN_APPLIES`). Uses `APPLYBOT_HEADLESS_UI=1` so dialogs do not block on stdin.

Use the **venv’s** `python` (not bare `python3` on macOS, which may stay on Homebrew and miss pytest):

```bash
./venv/bin/python -m pip install -r requirements.txt
export RUN_LINKEDIN_E2E=1
export MAX_APPLIED_JOBS=3
export APPLYBOT_HEADLESS_UI=1
./venv/bin/python -m pytest tests/e2e/test_live_linkedin_e2e.py -v
```

Do not paste trailing comments on the same line as `pip install` in zsh; a broken paste can leave `installs` as a stray command.

Shell equivalent: `./scripts/run_e2e_three_applies.sh` (from repo root, after `chmod +x`). Default GitHub Action uses `python -m pytest -m "not e2e"` so CI stays offline.

## 6. Run the Bot (Easy Apply)

If you use the venv from [§1](#1-clone-and-install), run the bot with that interpreter (avoids Homebrew `python3` ignoring the venv on macOS):

```bash
./venv/bin/python runAiBot.py
```

Or activate the venv (`source venv/bin/activate`) and run **`python3 runAiBot.py`** if `which python3` shows `venv/bin/python3`. Many macOS venvs have **no `python` shim** (`command not found: python`); prefer **`./venv/bin/python`** from the repo root. On Windows: `venv\Scripts\python.exe runAiBot.py`.

The bot will:

1. Open Chromium with your persistent profile.
2. Navigate to the LinkedIn Jobs search with your filters (watch for `f_EA=true` in the URL).
3. For each matching job: evaluate relevance (AI), click Easy Apply, answer questions, upload resume, submit.
4. Stop after `max_applied_jobs` successful submissions (see `config/settings.py`).

## 7. While it runs

- **`logs/log.txt`** — grep `f_EA=true`, `[DEBUG] Easy Apply modal opened`, `OFFLINE MODE`.
- **`logs/screenshots/`** — failures.
- **`all excels/all_applied_applications_history.csv`** / **`all_failed_applications_history.csv`** — outcomes.

**Stop:** Ctrl+C. If you close the browser, the bot tries one automatic re-init.

**Smoke test:** set `max_applied_jobs = 3` in `config/settings.py`, run once, then raise the cap.

**Problems:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## 8. Updating

```bash
git pull origin main
./venv/bin/python -m pip install -r requirements.txt --upgrade
```

Your `config/*.py` and `config/master_resume.json` are gitignored, so `git pull` never clobbers them.
