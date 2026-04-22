# Troubleshooting

## Missing `config/secrets.py`

`runAiBot.py` (normal run and `--validate-config`) exits early with code **2** if `config/secrets.py` is absent. Create it from the example: `cp config/secrets.example.py config/secrets.py`, then edit credentials. Or run `./venv/bin/python -m applybot.setup`.

## `name 'linkedIn' is not defined`

You have `config/questions.py` (or imports succeeded) but that file does **not** define **`linkedIn`** (capital **I**), and the compat shim only runs when `questions.py` is missing. The bot now backfills **`linkedIn`** from `config/answers.py` (`linkedIn` / `linkedin`) or `profile.json` (`linkedin_url`). If it is still empty, add to **`config/answers.py`**: `linkedIn = "https://www.linkedin.com/in/yourprofile"`.

## Login

- **Stuck on `https://www.linkedin.com/jobs/` after setup** — That URL is both the **public** jobs landing (login hero, “Millions of jobs…”) and a signed-in surface. The bot no longer treats bare `/jobs` as logged-in unless the **global nav** is visible; otherwise it runs `login_LN`. Same credentials path as `/login`; if the form is already on `/jobs/`, it fills there without redirecting.
- **“Welcome back” / remembered account** — With a saved browser profile, LinkedIn may show a card instead of email/password fields. The bot clicks **Sign in using another account** (or similar) when it sees that link so it can fill `secrets.py`. You can also click that link once manually.
- **Wizard wrote secrets** — use **email + password** on LinkedIn’s form, not only Google “Continue as”. The bot fills `config/secrets.py` into the email/password fields.
- **Stuck on login page** — finish CAPTCHA / 2FA / device prompts in the browser; the bot waits up to **3 minutes** after clicking Sign in.
- **Still failing** — confirm `config/secrets.py` matches your LinkedIn account; try logging in once manually so the saved browser profile keeps the session ([RUN.md — First-run login](RUN.md#4-first-run-login)).

## Session log / “Failed Logging”

The bot writes under `logs/` (e.g. `logs/session_YYYYMMDD.log`). If that folder was missing, older builds errored on first log line; current code creates `logs/` automatically. For non-interactive runs, set **`APPLYBOT_HEADLESS_UI=1`** so a log failure does not block on **Press Enter** in the terminal.

## Easy Apply / “Next” not clicking

See logs for `[DEBUG] Easy Apply modal opened`. If clicks fail, check `logs/screenshots/`. The bot uses `driver` (not the modal element) for JS fallbacks on **Next / Review / Submit**.

## AI offline

Log: `OFFLINE MODE`. Fix or add API keys in `config/secrets.py` (no `YOUR_*` placeholders).

## Filters / `f_EA=true`

Use `easy_apply_only = True` in `config/search.py` and preferably `use_url_filters_only = True` in `config/settings.py` so filters live in the URL, not the flaky UI. Details: **[LINKEDIN_URL_REFERENCE.md](LINKEDIN_URL_REFERENCE.md)**.

## Browser crashed

Close extra Chrome/Chromium windows using the same profile, then rerun. The bot tries one automatic browser re-init on session errors.

---

More: **[RUN.md](RUN.md)** · URL params: **[LINKEDIN_URL_REFERENCE.md](LINKEDIN_URL_REFERENCE.md)**
