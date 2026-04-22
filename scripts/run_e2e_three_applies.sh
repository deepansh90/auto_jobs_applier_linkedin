#!/usr/bin/env bash
# Live LinkedIn: run the bot up to MAX_APPLIED_JOBS (default 5) Easy Apply submissions.
# For CSV + JSONL assertions and pre-submit dumps, use pytest (see docs/RUN.md).
#
# Prerequisite: working config/secrets.py and an interactive LinkedIn session (or saved profile).
#
# Usage (from repo root):
#   chmod +x scripts/run_e2e_three_applies.sh
#   ./scripts/run_e2e_three_applies.sh
#
# Pytest (pre-submit field dump + CSV row delta; default min 5 applies):
#   RUN_LINKEDIN_E2E=1 LINKEDIN_E2E_MIN_APPLIES=5 MAX_APPLIED_JOBS=5 \
#     APPLYBOT_HEADLESS_UI=1 LINKEDIN_E2E_TIMEOUT_SEC=7200 \
#     ./venv/bin/python -m pytest tests/e2e/test_live_linkedin_e2e.py -v

set -euo pipefail
cd "$(dirname "$0")/.."
PY="./venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi
export MAX_APPLIED_JOBS="${MAX_APPLIED_JOBS:-5}"
export APPLYBOT_HEADLESS_UI="${APPLYBOT_HEADLESS_UI:-1}"
exec "$PY" runAiBot.py
