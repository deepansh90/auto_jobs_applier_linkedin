"""
Live LinkedIn E2E: run the real bot until at least N new rows appear in the
applications CSV (default N=3).

This is **opt-in** only. Default `pytest` runs skip these tests unless
`RUN_LINKEDIN_E2E=1` is set in the environment.

Requirements:
  - Valid `config/secrets.py`, personals, search terms, and Chrome/Chromium.
  - LinkedIn session that can complete Easy Apply flows.
  - `APPLYBOT_HEADLESS_UI=1` is injected so alerts do not block on stdin.

Set `MAX_APPLIED_JOBS` (injected here as 3) to stop the bot after enough successes.
"""

from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUN_BOT = ROOT / "runAiBot.py"

pytestmark = pytest.mark.e2e


def _applications_csv_path() -> Path:
    """Match bot defaults: prefer migrated history path, then legacy."""
    h = ROOT / "history" / "applications.csv"
    legacy = ROOT / "all excels" / "all_applied_applications_history.csv"
    if h.is_file():
        return h
    if legacy.is_file():
        return legacy
    return h


def _applied_row_count(path: Path) -> int:
    if not path.is_file():
        return 0
    with open(path, encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


@pytest.mark.skipif(
    os.environ.get("RUN_LINKEDIN_E2E", "").strip() != "1",
    reason="Live E2E disabled. Export RUN_LINKEDIN_E2E=1 to enable (applies to real jobs).",
)
@pytest.mark.skipif(
    not (ROOT / "config" / "secrets.py").is_file(),
    reason="Requires config/secrets.py",
)
def test_live_linkedin_at_least_three_new_applications_in_csv() -> None:
    csv_path = _applications_csv_path()
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    before = _applied_row_count(csv_path)
    min_new = max(1, int(os.environ.get("LINKEDIN_E2E_MIN_APPLIES", "3")))
    cap = max(min_new, int(os.environ.get("MAX_APPLIED_JOBS", str(min_new))))

    env = os.environ.copy()
    env["MAX_APPLIED_JOBS"] = str(cap)
    env["APPLYBOT_HEADLESS_UI"] = "1"

    timeout_s = int(os.environ.get("LINKEDIN_E2E_TIMEOUT_SEC", str(2 * 60 * 60)))

    proc = subprocess.run(
        [sys.executable, str(RUN_BOT)],
        cwd=str(ROOT),
        env=env,
        timeout=timeout_s,
    )
    assert proc.returncode == 0, (
        f"runAiBot exited {proc.returncode!r}. Check logs/log.txt and logs/screenshots/. "
        "If the session hit CAPTCHA or login, fix credentials or run interactively once."
    )

    after = _applied_row_count(csv_path)
    assert after - before >= min_new, (
        f"Expected at least {min_new} new Easy Apply rows in {csv_path} "
        f"(before={before}, after={after}). "
        "Widen search terms in config/search.py or lower filters if nothing matched."
    )
