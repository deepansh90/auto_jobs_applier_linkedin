# Troubleshooting Guide

Common issues and fixes for the LinkedIn Auto-Applier.

## "Next button not clicking" / `'WebElement' object has no attribute 'execute_script'`

**Symptom**: Easy Apply modal opens but the bot fails with repeated `Click Failed! Didn't find 'Next'` messages, or logs show an `AttributeError` about `execute_script`.

**Root cause**: Historically the first `Next` click was invoked with the modal `WebElement` as scope. When the JS-click fallback in `wait_span_click` ran, it called `scope.execute_script(...)`, which only exists on `WebDriver`.

**Fix (already applied in `runAiBot.py`)**:
- The first `Next` click now uses `driver` (the `WebDriver`) instead of `modal`.
- A `buffer(2)` delay is inserted after the modal is located so it fully renders before the first interaction.
- Additional XPath fallbacks are tried for the Next/Review/Submit button: `aria-label="Continue to next step"` and generic `aria-label~=Continue|Submit`.
- A JS click fallback is attempted via `driver.execute_script("arguments[0].click();", next_button)` if the native click raises an unexpected exception.

If the issue persists, check `logs/log.txt` for `[DEBUG]` lines around `Easy Apply modal opened` to inspect modal visibility/class and which fallback was triggered.

## "All AI providers failed" → Offline mode

**Symptom**: Log line `All AI providers unavailable. Running in OFFLINE mode (skipping AI-dependent features).`

**Cause**: Every configured provider is unusable — Gemini quota exhausted, OpenAI key missing or a placeholder, or all providers returned 401/429 errors.

**Behavior**: The bot no longer hard-fails. Instead, `ai_call` returns `{"error": "offline_mode", ...}` and the callers degrade gracefully:
- Job relevance check is skipped (job is not filtered out).
- Tailored resume generation is skipped.
- Skill extraction falls back to the string `"Offline mode - no AI extraction"`.
- Free-text / textarea questions fall back to defaults (e.g. `years_of_experience`) and are recorded in `randomly_answered_questions`.

**To restore AI**: Update valid API keys in `config/secrets.py` (replace `YOUR_*` placeholders) or wait for the Gemini quota window to reset.

## Easy Apply filter (`f_EA=true`)

Set `easy_apply_only = True` in `config/search.py`. The bot constructs the search URL via `build_linkedin_jobs_search_url(...)` and appends `&f_EA=true`. Verify in `logs/log.txt` that the resolved search URL contains `f_EA=true`.

## Browser session / `InvalidSessionIdException`

The bot now attempts one automatic re-init (`init_browser()` + re-login) when it hits `NoSuchWindowException`, `InvalidSessionIdException`, or `WebDriverException` at the top-level loop. If it still can't recover, close all Chrome/Chromium windows that may be holding the default profile and restart.

## Chromium vs Chrome

Set `use_chromium = True` in `config/settings.py` to use Chromium (installed via `brew install --cask chromium`). The bot auto-resolves the Chromium binary and uses a dedicated Chromium user data directory, so it won't conflict with your regular Chrome profile.

## Filter UI doesn't work / "Show results" button not found (pill layout)

LinkedIn A/B-tests its jobs page between a **classic** layout (the "All filters" button opens a modal with every filter) and a newer **pill-based** layout (individual pills for Easy Apply, Date posted, Experience level, etc., with a "Show N results" button at the bottom). The pill layout's "Show results" button has a different DOM that the bot may not match.

**Fix**: the default setting `use_url_filters_only = True` in `config/settings.py` skips the filter UI entirely. All filters are encoded directly in the search URL via `build_linkedin_jobs_search_url`:

- `f_EA=true` — Easy Apply
- `f_WT=1,2,3` — On-site / Remote / Hybrid
- `sortBy=DD` or `R` — Most recent / Most relevant
- `f_TPR=r2592000` — Past month (r604800 = Past week, r86400 = 24h)
- `f_JT=F` — Full-time (P / C / T / V / I / O)
- `f_E=1..6` — Experience level

If you want the old UI-driven behaviour, set `use_url_filters_only = False`.

## Form `<select>` vs custom dropdowns (combobox)

Native `<select>` elements are handled in `answer_questions`; custom widgets that use `role="combobox"` / a popover listbox without a `<select>` may not be filled automatically. If a question stalls, add a matching entry in `config/custom_questions.py` when the bot supports that field type, or answer that step manually once. Sticky job-search filters are applied via URL params and `reset_sticky_account_filters_once()`; if the Easy Apply pill looks wrong after load, check logs for `[INFO] Flipped sticky filter`.

## "Follow company" checked when `follow_companies = False`

The bot used to treat every checkbox in the form the same and **checked** unchecked boxes—including the employer follow checkbox. That is fixed: `follow-company-checkbox` is skipped during the generic question loop and only adjusted in `follow_company()` before submit, matching `follow_companies` in `config/settings.py`.

## Resume extraction wrong / `config/profile.json` has placeholders

The AI missed something or all providers are offline. Open `config/profile.json` and fix fields manually. You can also:

- Re-run extraction: delete `config/profile.json`, re-run the bot.
- Override specific values in `config/answers.py` (uncomment `first_name`, `linkedIn`, etc. at the bottom of the example). Values in `answers.py` always win over `profile.json`.

