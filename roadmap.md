# Roadmap

Deferred work. Nothing here blocks day-to-day use.

## Done

- Per-session log file `logs/session_YYYYMMDD.log` (`modules/helpers.py::get_log_path`).
- State-aware `boolean_button_click(..., desired_on=True)`.
- Sticky-filter reset on run start (Easy Apply / Under 10 / In network / Fair Chance) — `runAiBot.py::reset_sticky_account_filters_once`.
- Typeahead dropdown selection (Noida/city autocomplete).
- Stale-element resilience in Easy Apply multi-step form (`get_active_modal`, `_find_next_or_review_or_submit`, 3× retry around Next/Review/Submit).
- Hardened browser re-init on crash (`_reinit_browser_with_retry`).
- Offline-mode fallback when all AI providers are unavailable.
- Stripped upstream author/license headers and deleted `modules/__deprecated__/`.
- `DEBUG_VERBOSE` env flag gates all `[DEBUG]` lines via `dbg()` helper.
- Non-waiting already-applied DOM check (saves ~2 s per skipped job).
- Removed upstream sponsor URLs and `.github/FUNDING.yml`.
- **#11 Rewrite `README.md` + docs in own voice.** Completely distinct structure, no fork attributions.

## Deferred

### 1. `BotSession` class — kill module-level globals
`runAiBot.py` shares state via globals (`driver`, `wait`, counters) and
`from modules.* import *`. Wrap in a `BotSession` dataclass and pass
explicitly. High risk (many call sites), medium priority.

### 2. Narrow `except Exception:` to specific Selenium errors
Dozens of broad `try/except` blocks silently swallow
`StaleElementReferenceException`, `TimeoutException`, etc. Define a
small exception taxonomy (`RecoverableUiError`, `JobSkipped`,
`SessionDied`) and narrow catch sites. Medium risk, medium priority.

### 3. Decompose `runAiBot.py` into `core/` modules
Split the 2k-line file into `navigator.py` (URL builder + filters),
`ai_orchestrator.py` (dispatcher), `form_worker.py` (Easy Apply form),
`job_filter.py` (prefilter). High cumulative risk; do one extraction
per PR, e2e between each.

### 4. Typed centralized config
`config/*.py` is scattered. Replace with a `@dataclass Config` loaded
via `load_config() -> Config`. Keep existing user-editable files.
Low priority.

## Deferred speed wins (measured vs upstream)

Upstream is ~800 LoC smaller and snappier. Ranked by ROI:

- **#5 Sticky-reset cache** — cache toggle state in `logs/.sticky_state.json` per account; skip modal round-trip on subsequent runs. Saves 2–4 s/run.
- **#6 Trim excess `buffer()` calls** — we have 18 vs upstream's 14. Replace fixed delays after deterministic state changes with `WebDriverWait(...).until(...)`. Saves ~3 s per search term.
- **#7 Collapse dead UI-filter path** — `apply_filters` UI branch is ~120 LoC of dead code at default config (`use_url_filters_only=True`). Lazy-import only when needed.
- **#8 Per-run company caches** — cache `company -> blacklisted` and `company -> about_text` for the run. Saves repeat scroll+regex at same company.
- **#9 Tighter stale-element retry** — current retry sleeps 1 s × 3 = up to 3 s added. Drop to 0.3 s. Niche.

