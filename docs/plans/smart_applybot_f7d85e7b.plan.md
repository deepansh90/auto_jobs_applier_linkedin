ApplyBot Main3 Follow-Ups Plan

What Changed In -main-3 Vs -main-2

The new drop made real progress against the prior plan:

New applybot/job_matcher.py, applybot/answer_router.py, applybot/onboarding/profile_form.py, applybot/config_bootstrap.py, applybot/submit_button_helpers.py, applybot/resumes/generator.py.

Setup wizard rewritten to a 5-step flow with resume parsing, local-LLM detection, doctor button.

--doctor command wired in [applybot/__main__.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/__main__.py).

offline_mode_strategy introduced in [config/settings.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/config/settings.py).

Dead fix_excepts.py deleted; pytest.ini added.

The prior plan was even checked into [config/smart_applybot_f7d85e7b.plan.md](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/config/smart_applybot_f7d85e7b.plan.md).

But several pieces are wired wrong and will break a real run.

P0: Critical Regressions From -main-3 (Fix Today)

These items break the bot or silently corrupt config and should be fixed before everything else.

P0.1 Deterministic matcher uses the wrong dict shape

File: [applybot/job_matcher.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/job_matcher.py).

score_job_match reads master_resume.get("title", "") and master_resume.get("skills", []), but the synthesized resume from [config/_compat.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/config/_compat.py) returns { "personal_info": {...}, "summary_master": "...", "skills": { "technologies": [...] } } — no title, and skills is a dict not a list.

Result today: every job scores 0 → falls into score < 25 → "Deterministic Score Too Low" → bot skips every job when master_resume_data is synthesized from profile.json.

Fix:

Normalize the input: accept both skills: list and skills: { technologies: [...] }; derive title from personal_info.title or headline or summary_master if present.

Cap at a higher score (today max is 60: 20 title + 40 skills) so the >= 75 auto-approve branch is reachable.

Add a tiny test in [tests/](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/tests/) that feeds the _compat.synthesize_master_resume() output and asserts the score is non-zero for an obvious match.

 

P0.3 Wizard generates a custom_questions.py the rest of the bot cannot read

File: [applybot/onboarding/profile_form.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/onboarding/profile_form.py) generate_custom_questions writes custom_questions = [ {question, answer}, ... ].

But [applybot/__main__.py:115](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/__main__.py) does from config.custom_questions import custom_answers (a dict), and [applybot/pre_submit_verify.py:241](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/pre_submit_verify.py) requires the literal "custom_answers = {" to merge fixes.

Result: after the wizard, from config.custom_questions import custom_answers raises ImportError; pre-submit auto-fix is dead.

Fix:

Generate custom_answers = { "<skill>": "<years>", ... } to match the established convention used by __main__.py, pre_submit_verify.py, and custom_questions.example.py.

Keep a custom_questions = [...] alias only if the new answer_router is updated in the same change.

P0.4 answer_router imports the wrong symbols

File: [applybot/answer_router.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/answer_router.py).

from config.custom_questions import custom_questions — actual file exports custom_answers.

from config.answers import answers as legacy_answers — actual [config/answers.example.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/config/answers.example.py) exports top-level vars (desired_salary, notice_period, ...), no answers dict.

Result: router silently returns None for everything; the select/radio/text branches in fill_easy_apply_form fall through to the legacy heuristics — including the select_by_index(1) fallback in P0.6.

Fix:

Read custom_answers (dict). If it is missing, fall back to a list-of-dicts custom_questions for backward compat.

Drop the from config.answers import answers lookup; instead read the top-level vars by name (mirrors _compat.py).

Match keywords as whole-word regex (\b<key>\b), not substring — today "java" matches "javascript", "no" matches "knowledge".

Return (answer, source, confidence) so the form filler can record provenance for the audit and learning loop.

P0.5 Wizard does not escape strings into generated .py files

File: [applybot/onboarding/profile_form.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/onboarding/profile_form.py).

Examples that crash:

first_name = "{data.get('first_name', '')}" blows up if the name contains " (e.g. "Mary "Mae" Lou").

linkedin_summary = """{data.get('summary', '')}""" blows up if the summary contains """ or unbalanced backslashes.

desired_salary = {int(data.get('desired_salary', 0))} raises ValueError on empty string or commas.

Fix:

Use json.dumps(value) for every string (json.dumps is a valid Python literal for str).

Coerce salary/years/notice numbers safely (int(re.sub(r"[^\d]","", str(v) or "0") or 0)).

Add a unit test that feeds nasty inputs (quotes, newlines, triple-quotes, empty, very long) and runs compile() on the generated source.

P0.6 select_by_index(1) wrong-answer fallback still present

File: [applybot/__main__.py:2245](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/__main__.py).

After all routing fails, the select silently picks the first non-placeholder option. This is the original "wrong legal/visa/EEO answer" footgun the prior plan flagged.

Fix:

Replace with strict_answers setting from prior plan: skip the application or pause for human, never silently pick.

Pair with new answer_router precedence so this is reached only on truly unknown labels.

P0.7 Wizard parse_resume overwrites secrets.py without LinkedIn creds

File: [applybot/setup.py:447-471](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/setup.py).

The /parse_resume route writes secrets.py containing only AI keys, no username/password. If the user closes the tab between step 2 and step 5, --validate-config fails because username is missing.

Fix:

In /parse_resume, read existing secrets.py if present and merge — or skip writing secrets.py here entirely and pass the API key directly to ensure_profile.

Mark setup atomic via config/.setup_complete: doctor refuses to run unless that file exists.

P0.8 Wizard placeholder injection is broken

File: [applybot/setup.py:421-426](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/setup.py).

_inject_placeholder_examples calls .replace("you@example.com", ...) and .replace("Password", ...) but those literals are no longer in the rewritten template; placeholders never render.

Fix: either restore the __PH_*__ markers in the template, or delete the helper.

P0.9 Tests missing for the new modules

No tests under [tests/](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/tests/) cover job_matcher.py or answer_router.py.

Add: skill-shape compatibility, hard-filter false positives (Secret vs top secret clearance vs trade secret), router precedence and whole-word matching, generated custom_answers.py round-trip.

P1: Pending High-Impact Items From The Prior Plan

These are still applicable; they were not addressed in -main-3. Reuse the prior detail in [config/smart_applybot_f7d85e7b.plan.md](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/config/smart_applybot_f7d85e7b.plan.md).

 P2 (prior P5) Collapse duplicate ai_text_answer and ai_evaluate_resume definitions, defensive ai_check_error, per-provider model name handling, resilient resume_gen.py.

P3 (prior P4) Stabilize Selenium: clickable waits, bounded retry on stale list, scoped Easy Apply modal, platform-correct Keys.CONTROL/Keys.COMMAND, csv.DictReader for applied-id loading, lightweight checkpointing.

P4 (prior P6) Privacy and logging hardening: allow_cloud_ai consent, redact email/phone in print_lg by default, gate AI prompt/answer logging behind DEBUG_VERBOSE, lock [app.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/app.py) to 127.0.0.1 with token.

P5 (prior P7) Local LLM first-class: provider config helper, optional /models health check, OpenAI-compatible resume autofill, docs.

P6 (prior P10) Operator AI: post-batch analyzer (runAiBot.py --operator-review) producing session digest, tuning suggestions, and risk flags using only local LLM by default.

P7 (prior P11) Quick wins: configurable cycle_sleep_seconds, --dry-run-applies, per-job timeout, per-company cap, .env support via existing python-dotenv, "Why this job?" log line, drop flask-cors, consolidate CI workflows.

Additional Rated Findings From Re-Audit

Ratings: Impact = user/business/runtime severity. Risk = implementation risk. Do it? = priority recommendation.

ID

Change

Evidence / Location

Impact

Risk

Do it?

Why

A1

Make wizard-generated secrets.py complete

[applybot/setup.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/setup.py) /submit writes username, password, use_AI, ai_provider, API keys only; [validator.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/validator.py) and provider clients expect llm_api_url, llm_model, llm_spec, stream_output, showAiErrorAlerts.

Very High

Low

Must do now

A user can complete onboarding, click Validate, and still fail validation or AI init.

A2

Fix resume autofill import/order bug

[applybot/__main__.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/__main__.py) runs ensure_profile before default_resume_path from questions.py is imported.

High

Low

Must do now

The bot can parse the wrong root resume.pdf instead of the wizard-selected resume.

A3

Use sys.executable in wizard doctor

[applybot/setup.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/setup.py) run_doctor() calls python -m applybot --doctor.

High

Very Low

Must do now

On macOS/Linux, python may be missing or outside the venv, so the wizard validation result is misleading.

A4

Add --doctor to runAiBot.py CLI

[runAiBot.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/runAiBot.py) supports only --help and --validate-config; doctor only works through python -m applybot --doctor.

Medium

Low

Should do

Users will naturally try ./venv/bin/python runAiBot.py --doctor; one canonical CLI avoids confusion.

A5

Make tailoring resilient to minimal master_resume_data

[applybot/resumes/resume_gen.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/resumes/resume_gen.py) expects education and patents; _compat.synthesize_master_resume() omits them.

High

Low

Must do now

High-match path can crash right after AI relevance succeeds.

A6

Separate session blacklist from configured company blocklist

[applybot/__main__.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/__main__.py) passes session blacklisted_companies set to job_matcher as blacklisted_companies.

Medium

Medium

Should do

The name implies user config but actually means companies rejected during this session. Bad mental model and future bug risk.

A7

Normalize numeric config values after overlay

[applybot/__main__.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/__main__.py) computes salary/notice derived fields at import time; overlay can make numeric values strings.

Medium

Low

Should do

Hand-edited user.settings.json or wizard strings can crash before main().

A8

Stop logging AI answers by default

[applybot/ai/openaiConnections.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/ai/openaiConnections.py) logs every AI answer; [helpers.print_lg](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/helpers.py) writes raw messages to session log.

High

Low

Must do before wider use

Logs can contain salary, visa, phone, email, employer, free-text answers. Gate behind DEBUG_VERBOSE=1 and redact PII.

A9

Add token/auth to applied-jobs Flask API

[app.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/app.py) returns full application CSV rows to anyone who can reach /applied-jobs.

Medium

Low

Should do

Bound to localhost by default, but accidental 0.0.0.0 or port forwarding leaks history.

A10

Consolidate CI workflows

[.github/workflows/pytest.yml](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/.github/workflows/pytest.yml) and [verify.yml](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/.github/workflows/verify.yml) run different Python versions and commands.

Medium

Low-Medium

Should do soon

Conflicting CI signals slow every future fix.

A11

Fix README/RUN repo path drift

[README.md](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/README.md), [docs/RUN.md](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/docs/RUN.md).

Medium

Very Low

Should do now

New users copy commands that reference another repo/folder name.

A12

Pin loose dependencies / split dev deps

[requirements.txt](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/requirements.txt) includes loose libs and test deps mixed with runtime.

Medium

Low

Should do soon

Avoids "worked yesterday" dependency breakage; improves install clarity.

A13

Extract shared applied-jobs CSV path helper

[app.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/app.py), E2E helper duplicate history/ vs legacy path logic.

Low-Medium

Low

Do with tests

Small DRY win and catches migration path regressions.

A14

Rename root test_regex.py

[test_regex.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/test_regex.py) is a side-effect script matching pytest discovery naming.

Low-Medium

Very Low

Should do now

Prevents accidental noisy test import when someone runs bare pytest.

A15

Add pyproject.toml

Missing at repo root.

Low-Medium

Low-Medium

Nice to do after P0

Centralizes ruff/black/mypy/pytest config and enables pip install -e ..

A16

Tighten apply_user_overlay unknown keys

[applybot/config_loader.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/config_loader.py) can attach unknown JSON keys to settings silently.

Low

Low

Optional

Avoids silent typos in user.settings.json.

A17

Fix .gitignore stale / wrong learned answer path

[.gitignore](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/.gitignore) ignores auto-job-apply-profile/config/learned_answers.json, not local config/learned_answers.json; contains odd claude integration.

Medium

Very Low

Should do now

Learned answers can contain PII and should be ignored in the actual repo path.

A18

Teach validator compat mode or require generated modules explicitly

[validator.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/validator.py) imports config.personals / questions directly even though _compat.py supports profile-only mode.

Low-Medium

Medium

Consider

If wizard always generates modules, this is less urgent; if profile-only setup remains supported, it must be fixed.

Do-Now Shortlist

These are the highest value additions to the current P0 list:

A1 + P0.7 together: make setup-generated secrets.py complete and stop /parse_resume from writing partial secrets.

A2: move ensure_profile until after resolved default_resume_path.

A3 + A4: one reliable doctor path using sys.executable, exposed through both python -m applybot --doctor and runAiBot.py --doctor.

A5: make resume_gen.py tolerate missing optional sections.

A8 + A17: stop logging AI answers by default and ignore the actual learned-answer path.

A10 + A11 + A14: CI/docs/test-discovery hygiene so future contributors do not fight the repo.

Suggested Order

P0.1, P0.2, P0.3, P0.4, P0.5 in one PR — these together unblock a real end-to-end run.

P0.6, P0.7, P0.8, P0.9 in a second PR — safety + tests around the new wizard/answer paths.

Prior P1 (fail-closed AI + cooldown/budget) — needed before anyone runs the bot at scale on Gemini free tier.

P3 Selenium hardening + P7 quick wins — biggest reliability/UX bang for the buck.

P5 local LLM first-class, then P6 Operator AI on the now-clean data.

Risk Notes

P0.1 fix changes which jobs get auto-approved by the deterministic matcher. Land it together with a JSONL decision log so the user can audit a few sessions before relying on auto-approval.

P0.3 + P0.4 + P0.5 touch generated config files; gate behind a backup of any existing custom_questions.py/personals.py/questions.py to a .bak before overwrite.

P0.6 will increase pause/skip frequency until custom_answers is populated. Default strict_answers = False for the first release with a clear log warning, then flip to True after a beta period.

Cross-Functional Enhancement Layer

These items are net-new additions on top of P0-P7. They come from a five-persona review (Lead Engineer, UX Designer, Growth PM, QA Automation, Viral Marketer) and target what an "elite" v1 release would look like.

P8: Steve Jobs UX Layer

Goal: the wizard, terminal output, and generated artifacts all feel pixel-perfect, focused, and self-explanatory.

Wizard restyle (single design system): centralize colors, spacing, type-scale into applybot/templates/_design.css. One typography scale (12/14/16/24/32), one neutral palette + one accent (LinkedIn blue). Strip the multiple inline <style> blocks in [applybot/setup.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/setup.py).

Drop the noise: remove the "Build your career / Stay updated" filler subtitle; replace with one outcome-oriented line per step ("Connect your LinkedIn", "Show us your resume", "Confirm your answers", "You're ready").

Inline validation: validate email, phone, salary, and resume path on blur with a 4-color status (neutral/warning/error/success) instead of alert(). Use a shared <x-input> web component to enforce one input style everywhere.

Loading is visible: the resume parse step today disables a button silently for several seconds. Add a 3-stage progress (Reading PDF → Extracting facts → Drafting answers) with skeleton placeholders for the fields about to be populated.

Autosave + recover: every field edit persists to localStorage so closing the tab does not lose progress. On reopen, the wizard restores state and asks "Continue where you left off?".

Success page that does the work: instead of telling the user to copy-paste a terminal command, show a single primary CTA "Start applying" that calls a new POST /run endpoint to spawn runAiBot.py, plus a secondary "Open terminal command" for power users. Also embed a live tail of logs/log.txt for the first minute.

Friendly generated configs: every generated .py starts with a 3-line header explaining what it is and how to safely edit it; section headers use # ─── Salary & Notice ─── style banners.

Quiet terminal by default: route routine print_lg lines through a single status formatter ([09:41] applied — Senior Engineer @ Acme (score 82)); reserve multi-line output for errors. Hide DEBUG noise unless DEBUG_VERBOSE=1.

One icon, one favicon: add applybot/static/favicon.svg and reference it from the wizard so it does not look like an unfinished local server.

P9: Product Manager Zero-Friction Layer

Goal: someone with zero CLI experience can go from "open the link" to "first application" in under three minutes.

Collapse to 3 effective steps: keep the 5-step UI, but mark steps 4 (preferences) and 5 (skill years) as optional with sensible defaults derived from the resume. The user can finish setup after step 3 and tune later via runAiBot.py --reconfigure.

Resume drag-and-drop: replace the "type the absolute path" field with a real file uploader; copy the PDF into auto-job-apply-profile/resume.pdf automatically. Today asking for an absolute path is the single biggest abandonment point.

One-click "Start applying": see P8.6.

--reconfigure mode: ./venv/bin/python -m applybot.setup --reconfigure search reopens just the relevant step, prefilled. Avoids re-entering everything to change one field.

--first-job smoke mode: runAiBot.py --first-job opens the bot, navigates one Easy Apply, fills the form, screenshots the pre-submit modal, and exits without submitting. Builds confidence and surfaces missing answers immediately.

.env auto-bootstrap: wizard writes LI_USERNAME, LI_PASSWORD, GEMINI_API_KEY into .env (already in .gitignore) instead of secrets.py, eliminating the "secrets in source files" anti-pattern.

Onboarding telemetry (opt-in): when the user clicks "Allow anonymous usage stats", post the funnel event (step reached, time spent) to a self-hosted endpoint. No PII. Lets the team see exactly where users drop.

First-run tour: on the success page, a 30-second guided tour highlights the live log tail, the history/applications.csv, and the --reconfigure command.

Empty-state coaching: if config/profile.json ends up sparse, the success page displays "We couldn't read X, Y, Z from your resume. Click here to fill them in" — with the relevant fields prefilled and ready to edit.

P10: Architecture / DRY Refactor

Goal: codebase a senior contributor can ramp into in a day; passes ruff, black, mypy --strict on changed files.

Decompose [applybot/__main__.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/__main__.py) (~3650 lines) into:

applybot/bot/login.py — LinkedIn login + session detection

applybot/bot/search.py — URL builder, filters, pagination

applybot/bot/form_filler.py — fill_easy_apply_form + helpers

applybot/bot/relevance.py — deterministic + AI relevance pipeline

applybot/bot/session.py — main loop, recovery, cycle sleep

applybot/bot/persistence.py — applied-jobs CSV, decision JSONL, learned answers

Keep applybot/__main__.py as a thin orchestrator.

Share AI provider code: [applybot/ai/openaiConnections.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/ai/openaiConnections.py) and [applybot/ai/geminiConnections.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/ai/geminiConnections.py) duplicate ~70% of structure. Extract applybot/ai/base.py with AIProvider abstract class (extract_skills, answer_question, check_relevance, generate_resume); concrete providers only override transport.

Single config bootstrap: every module that does from config.<x> import * should instead call applybot.config_bootstrap.load(). Eliminates import-order bugs documented in P3 of the prior plan.

Split applybot/helpers.py into helpers/logging.py (file + console + audit), helpers/json_utils.py (the convert_to_json + new schema validator), helpers/dialog.py (smart_confirm), helpers/retry.py. helpers.py becomes an index re-export.

One config-file generator path: profile_form.generate_*, the wizard submit(), and setup.py /parse_resume all write secrets.py. Centralize in applybot/config_writer.py with write_section(name, payload) and merge(name, patch).

Type hints + dataclasses: JobDecision, AnswerRecord, ProfileFacts, MatchResult, WizardPayload, ProviderConfig. Eliminates the dict-shape regression from P0.1 and P0.4 by construction.

Lint/format gates: add ruff + black + mypy to [.github/workflows/](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/.github/workflows/), pre-commit config, and a make format target. Consolidate pytest.yml and verify.yml into one matrix workflow.

Naming pass: rename _compat.py → legacy_compat.py, submit_button_helpers.py content into bot/form_filler.py, etc.

P11: QA Automation Layer

Goal: regression confidence without depending on a real LinkedIn run.

Mocked DOM unit tests for fill_easy_apply_form: stub WebElement and Select via small fakes; cover all branches (text, textarea, select, radio, checkbox, date) including the new answer_router path. Today the function is 600+ lines with zero unit coverage.

Generated-config compile test: tests/test_profile_form_compile.py feeds adversarial inputs (quotes, newlines, unicode, empties, very long strings) to generate_all_configs, then compile() and importlib.import_module each generated file. Catches P0.5 regressions automatically.

Snapshot tests for the wizard HTML: pytest --snapshot-update ensures the design-system refactor (P8) does not silently break form ids the JS depends on.

Coverage gate: pytest --cov=applybot --cov-fail-under=70. Start at 50, raise quarterly.

Recorded LinkedIn HAR replay: capture an Easy Apply flow with mitmproxy once, then replay it in CI (tests/e2e/test_replay_easy_apply.py). Avoids depending on a live LinkedIn account in CI while still exercising real selectors.

Mutation testing on critical helpers: run mutmut on [applybot/job_matcher.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/job_matcher.py), [applybot/answer_router.py](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/applybot/answer_router.py), pre_submit_verify.audit_questions_list. Targets ≥ 80% mutant kill.

Flask endpoint tests: tests/test_setup_api.py covers every wizard route with both happy and adversarial payloads (oversized JSON, missing keys, path traversal in resume_path).

Crash-only safety test: kill the process at random points during submit() and verify config files are either fully written or unchanged (atomic writes with os.replace).

P12: Growth & Virality Layer

Goal: organic distribution loop where each successful run generates a shareable artifact and an upgrade nudge.

Shareable session digest: at session end (P10 of the prior plan), generate logs/session_<ts>/share.png — a 1200×630 OG image summarizing "ApplyBot applied to N jobs in M minutes — top match: X". One-click Copy share link button on the success page.

README hero GIF: record a 30-second wizard-to-first-apply screencast, embed at the top of [README.md](/Users/deepanshrawal/Downloads/auto_jobs_applier_linkedin-main-3/README.md). Currently the README is text-only and visually flat.

One-line install command: curl -fsSL apply.bot/install | sh shim that wraps git clone + venv + pip install -r requirements.txt + python -m applybot.setup. Cuts the install steps from ~5 to 1.

--share-stats opt-in: anonymized weekly stats POST to a community endpoint (jobs applied, avg score, time saved). The community page leaderboard creates social proof and a backlink.

--export-portfolio: zips resume_output/ (tailored resumes per company) into portfolio.zip for sharing on LinkedIn — every share is a passive ApplyBot ad.

Public roadmap + Discord: add ## Community section in README pointing to a Discord invite (single source of issues + early adopters).

Branded artifact comments: generated tailored resumes include a footer Generated by ApplyBot — apply.bot that the user can remove if desired (default on, opt-out via setting).

Friendly upgrade nudge: at startup, optionally check https://apply.bot/version.json (cached 24h) and print a one-line [ApplyBot v1.4 → v1.5 available]. Never auto-update.

Referral hook (optional): if --share-stats is on and the user generates 10+ applies, the success page offers Invite a friend, both get N more daily applies. Keep ethical — must be opt-in and skippable.

Updated Suggested Order

P0 (regressions) ship first. Without these the bot does not work.

P10 architecture refactor + P11 QA harness in parallel. Doing them now means every later change is cheaper and safer.

P8 + P9 (UX + zero-friction) as a single "v1.0 polish" milestone. Highest perceived quality lift; depends on the architectural cleanup so the wizard refactor does not have to re-thread import order.

Prior P1, P3, P4, P5, P6, P7 as tracked in the body above.

P12 (growth) only after the bot is reliable enough that a viral push will not cause a wave of broken-install bug reports.

Note On "Refactored Code"

The prompt asked for the refactored code inline. Plan mode is read-only; the actual rewrite (especially P8 design system, P10 module split, and P12 shareable digest) requires file edits across applybot/, applybot/bot/, applybot/ai/, applybot/templates/, tests/, .github/workflows/, and the README. To execute, switch to agent mode and start with P0 + P10 (parallel), since those unlock everything else.