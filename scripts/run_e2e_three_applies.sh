#!/usr/bin/env bash
# Live LinkedIn E2E: applies up to MAX_APPLIED_JOBS (default 3) Easy Apply roles.
# Prerequisite: working config/secrets.py and an interactive LinkedIn session (or saved profile).
#
# Usage (from repo root):
#   chmod +x scripts/run_e2e_three_applies.sh
#   ./scripts/run_e2e_three_applies.sh
#
# Or via pytest (same effect, plus CSV row-count assertion):
#   RUN_LINKEDIN_E2E=1 ./venv/bin/python -m pytest tests/e2e/test_live_linkedin_e2e.py -v

set -euo pipefail
cd "$(dirname "$0")/.."
PY="./venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi
export RUN_LINKEDIN_E2E="${RUN_LINKEDIN_E2E:-1}"
export MAX_APPLIED_JOBS="${MAX_APPLIED_JOBS:-3}"
export APPLYBOT_HEADLESS_UI="${APPLYBOT_HEADLESS_UI:-1}"
exec "$PY" runAiBot.py
