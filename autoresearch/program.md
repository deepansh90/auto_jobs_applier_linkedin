# autoresearch: job-fit scorer

Adapted from karpathy/autoresearch (via miolini/autoresearch-macos). Same loop, different target:
instead of a GPT training script, the agent improves the **deterministic job-fit scorer** the LinkedIn
bot uses to decide apply vs skip - measured against the human's own labels.

**The one user job:** rank jobs so the ones Deepansh would genuinely want float above the ones he would not.

## Files

| File | Who edits | Role |
|---|---|---|
| `autoresearch/candidate_scorer.py` | **agent (only this file)** | scoring logic, starts as a copy of production `score_job_match` |
| `autoresearch/prepare.py` | nobody | frozen evaluator: loads labels, prints `dev_auc` + guardrails |
| `autoresearch/data/labels.jsonl` | human only | ground truth from `label.py` |
| `autoresearch/program.md` | human | this file |
| `autoresearch/results.tsv` | agent (untracked) | experiment log |

## Setup (do once, with the human)

1. Propose a run tag from today's date (e.g. `nov13`). Branch `autoresearch/<tag>` must not exist. `git checkout -b autoresearch/<tag>`.
2. Read `candidate_scorer.py`, `prepare.py`, and `applybot/job_matcher.py` for context.
3. Check `./venv/bin/python autoresearch/prepare.py`. If it exits with code 2 ("not enough labels"), STOP and tell the human to run `./venv/bin/python autoresearch/label.py` (and to run the bot with `AUTOAPPLY_CAPTURE_JDS=1` to collect more jobs). Do not invent, import, or infer labels. (Rule of thumb for the human: 30+ labels unlocks the dev loop, ~75+ unlocks the holdout check, 100-150 makes results trustworthy.)
4. Create `autoresearch/results.tsv` with the header only. Record the baseline from the first run unmodified.

## Experimenting

Each run takes seconds: `./venv/bin/python autoresearch/prepare.py > autoresearch/run.log 2>&1`, then
`grep -E "^(dev_auc|recall_at_threshold|guardrails)" autoresearch/run.log`.

**You CAN:** change anything in `candidate_scorer.py` - weights, new signals (seniority, years-of-experience mentions, tech-stack overlap, red-flag phrases like "fresher"/"walk-in", title/stack mismatch), normalisation, saturation of repeated matches. Pure stdlib text logic only.

**You CANNOT:**
- edit `prepare.py`, `data/`, `config/`, `applybot/`, or any other file
- run the bot, open LinkedIn, or submit anything
- read hold-out results (`--holdout`) - that is for the human, once, at the end
- use network, files, LLM calls, or randomness in the scorer (guardrails reject this)
- hardcode a job id or company name from the labels (rejected, and it is overfitting anyway)

**Goal:** highest `dev_auc` with `guardrails: PASS`. A run with `guardrails: FAIL` (recall of jobs you'd apply to fell below production's, capped at 0.80) or a crash is a discard. `production_auc` in the output is today's bot on the same labels - your real gain is `dev_auc - production_auc`.

**Simplicity criterion:** with ~30-100 labels, AUC differences of 0.01-0.02 are noise. Keep a change only if it is a clear gain *and* explainable in one sentence ("penalise 'fresher' roles"). A tiny gain that adds ugly special cases is a discard. Deleting logic at equal AUC is a win. Prefer fewer, human-explainable signals over many tuned constants.

## Log (`results.tsv`, tab-separated)

```
commit	dev_auc	recall	status	description
```
status = `keep` | `discard` | `crash`. Use `0.0000` for crashes.

## Loop

1. `git log -1` - know where you are.
2. Make one change to `candidate_scorer.py`. Commit.
3. Run `prepare.py`, read the three grep lines (never dump the whole log).
4. Crash -> `tail -n 30 autoresearch/run.log`; fix trivial bugs, otherwise log `crash` and move on.
5. Improved AND guardrails PASS AND the change is explainable -> `keep`. Otherwise `git reset --hard HEAD~1` and log `discard`.
6. Repeat.

**Stop** after 40 experiments, or 12 in a row with no keep, then write a summary: baseline vs best `dev_auc`, the kept changes in plain English, and which ideas failed. (Unlike the original, evaluation is seconds not minutes, so the signal saturates fast - do not loop forever on 50 labels.)

## Promotion (human step - the agent never does this)

1. Human runs `./venv/bin/python autoresearch/prepare.py --holdout` once. If hold-out AUC is much lower than dev AUC, the loop overfit: reject or label more jobs.
2. If it holds up, port the kept logic into `applybot/job_matcher.py:score_job_match` via a normal reviewed change, and run `./venv/bin/python -m pytest tests -q`.
3. Real-world feedback (callbacks, rejections) is too slow to loop on; use it to refresh labels every few weeks.
