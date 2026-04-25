# Run Guide

How to install dependencies and run the bot on your local machine.

## Prerequisites

- **macOS or Linux** (tested on macOS 15). Windows works but is not the primary target.
- **Python 3.10+** (3.13 recommended). Check with `python3 --version`.
- **Chromium** (recommended) or Google Chrome.
  - Windows (PowerShell): `winget install Hibbiki.Chromium --accept-source-agreements --accept-package-agreements`
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

`--validate-config` and a normal run both require `config/secrets.py`. If it is missing, the CLI exits with code **2** and prints `cp config/secrets.example.py config/secrets.py` on stderr. With `use_AI = False` in `secrets.py`, validation skips LLM URL/key/model checks so you can confirm the rest of the config without API keys.

In CI, only `--help` / setup `--dry-run` are guaranteed without secrets; see `tests/test_cli.py` and `tests/test_config_bootstrap.py`.

To reset the local pytest cache: `rm -rf .pytest_cache` (the directory is listed in `.gitignore` and should not be committed).

Live LinkedIn pytest (real applies, pre-submit JSONL dumps): see **[§7 Live E2E (optional regression)](#7-live-e2e-optional-regression)** below.

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

### AI relevance: skip low-fit jobs (optional)

The bot already calls **`check_relevance`** when `use_AI` is on and a job description is available. By default, scores below **85** only disable **tailored resume**; Easy Apply can still run.

| Environment variable | Behavior |
|------------------------|----------|
| `APPLYBOT_STRICT_RELEVANCE=1` | If AI returns a parseable **`match_score`** and it is **strictly below** the minimum, the job is skipped (same `skip` path as other filters—no Easy Apply). Truthy values: `1`, `true`, `yes`, `on` (case-insensitive). |
| `APPLYBOT_RELEVANCE_MIN_SCORE` | Integer **1–100**, default **70**. Jobs with `match_score` below this value are skipped when strict mode is on. |

**Offline / errors:** Offline relevance, API error responses, or missing `match_score` leave no score to compare—strict mode does **not** skip in those cases.

### Pre-submit evidence and audit (optional)

Use this for a **verification pass** (for example cap applies at **20** without editing `config/settings.py`) and to capture what the form contains right before **Submit application**.

**Cap applies for one run** — the process reads `MAX_APPLIED_JOBS` at startup and overrides `max_applied_jobs`:

```bash
MAX_APPLIED_JOBS=20 ./venv/bin/python runAiBot.py
```

For the first manual check, set **`pause_before_submit = True`** in `config/questions.py` (or your overlay) so the bot pauses on the final screen; combine with the env vars below.

| Environment variable | Behavior |
|------------------------|----------|
| `APPLYBOT_PRE_SUBMIT_SCREENSHOTS=1` | After **Follow** (company) and before submit: full-page screenshot under `history/screenshots/pre_submit/`, plus a modal screenshot when the browser supports it. |
| `APPLYBOT_PRE_SUBMIT_DUMP` | Path to a JSONL file: one line per job with **`questions`** (what the bot filled from `questions_list`, source of truth) plus **`fields`** (DOM snapshot; if empty, the bot also probes `.jobs-easy-apply-modal` / `.artdeco-modal` on the driver). |
| `APPLYBOT_SUBMITTED_QA_JSONL` | Optional second path: append **only** `{ts, job_id, job_link, questions}` per job (no DOM) for easy grepping. |
| `APPLYBOT_PRE_SUBMIT_AUDIT=1` | Compare filled answers to `config/profile.json`: **skill + years** (conservative), plus light **email / phone / first name** substring checks. Without `profile.json`, mismatch checks are skipped (a log line is printed). |
| `APPLYBOT_PRE_SUBMIT_AUDIT_JSONL` | Optional path for audit JSONL (default: `logs/pre_submit_audit.jsonl` under the repo root). Each line includes `mismatches`, `has_high_severity`, and `actions_taken`. |
| `APPLYBOT_PRE_SUBMIT_AUDIT_STRICT=1` | If the audit finds a **high-severity** mismatch (skill/years only today), **skip submit**, write dump/screenshots if enabled, call **Discard**, and move on (job is not logged as submitted). Low-severity rows (email, etc.) are logged but do not trigger strict skip. |
| `APPLYBOT_AUTO_FIX_CUSTOM_ANSWERS=1` | With **strict** audit and a high-severity mismatch, merge suggested `(keyword, years)` pairs into **`config/custom_questions.py`** only (never `questions.py` / `answers.py`). Requires that file to exist (copy from `config/custom_questions.example.py`). |

**Important:** Updating `custom_answers` does **not** reload the in-memory map for the current modal; fixes apply from the **next** job onward unless you add a refill step later.

Screenshots and JSONL can contain **PII**; paths are under gitignored `history/` / `logs/` — do not commit them.

**Security / exports:** Never commit `config/secrets.py`. When creating a zip or archive, exclude it (e.g. `zip -r repo.zip . -x 'config/secrets.py'`). Prefer environment variables for credentials; see comments in `config/secrets.example.py`.

**AI keys:** If `use_AI` is `True` but your Gemini/OpenAI key is empty, the bot logs a **startup warning** and runs in offline fallbacks—set real keys in `secrets.py` or env (`GEMINI_API_KEY`, etc.).

**Native `<select>` questions:** After keyword/fuzzy matching fails, the bot can call **AI with the visible option list** (`single_select`) before falling back to a random option. OpenAI and Gemini prompts both include the option list when `use_AI` is on.

## 7. Live E2E (optional regression)

Opt-in only (`RUN_LINKEDIN_E2E=1`). Runs the real browser against LinkedIn and asserts the applications CSV grew by at least **5** rows by default (`LINKEDIN_E2E_MIN_APPLIES` / `MAX_APPLIED_JOBS`). Uses `APPLYBOT_HEADLESS_UI=1` so dialogs do not block on stdin.

The pytest harness sets **`APPLYBOT_PRE_SUBMIT_DUMP`** to a temp JSONL file: before each final **Submit application** click, the bot appends a line with visible `input` / `textarea` / `select` values for a quick sanity check (name or phone substring). LinkedIn’s DOM varies; spot-check the real confirmation UI when in doubt.

Use the **venv’s** `python` (not bare `python3` on macOS, which may stay on Homebrew and miss pytest):

```bash
./venv/bin/python -m pip install -r requirements.txt
export RUN_LINKEDIN_E2E=1
export MAX_APPLIED_JOBS=5
export LINKEDIN_E2E_MIN_APPLIES=5
export APPLYBOT_HEADLESS_UI=1
export LINKEDIN_E2E_TIMEOUT_SEC=7200
./venv/bin/python -m pytest tests/e2e/test_live_linkedin_e2e.py -v
```

Do not paste trailing comments on the same line as `pip install` in zsh; a broken paste can leave `installs` as a stray command.

Shell helper (runs the bot only, no pytest assertions): `./scripts/run_e2e_three_applies.sh` from repo root (after `chmod +x`). Default GitHub Action uses `python -m pytest -m "not e2e"` so CI stays offline.

## 8. While it runs

- **`logs/log.txt`** — grep `f_EA=true`, `[DEBUG] Easy Apply modal opened`, `OFFLINE MODE`.
- **`logs/screenshots/`** — failures.
- **`all excels/all_applied_applications_history.csv`** / **`all_failed_applications_history.csv`** — outcomes.

**Stop:** Ctrl+C. If you close the browser, the bot tries one automatic re-init.

**Smoke test:** set `max_applied_jobs = 3` in `config/settings.py`, run once, then raise the cap.

**Problems:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## 9. Updating

```bash
git pull origin main
./venv/bin/python -m pip install -r requirements.txt --upgrade
```

Your `config/*.py` and `config/master_resume.json` are gitignored, so `git pull` never clobbers them.
