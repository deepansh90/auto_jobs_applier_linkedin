"""
Subprocess CLI smoke tests (no browser).

`--validate-config` is optional in CI because it requires a real `config/secrets.py`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUN_BOT = ROOT / "runAiBot.py"


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
        **kwargs,
    )


def test_run_aibot_help_exits_zero():
    r = _run([str(RUN_BOT), "--help"])
    assert r.returncode == 0, r.stderr
    assert "validate-config" in r.stdout
    assert "applybot.setup" in r.stdout


def test_run_aibot_help_short_flag():
    r = _run([str(RUN_BOT), "-h"])
    assert r.returncode == 0
    assert "Easy Apply" in r.stdout or "easy apply" in r.stdout.lower()


def test_run_aibot_unknown_option_exits_nonzero():
    r = _run([str(RUN_BOT), "--not-a-real-flag"])
    assert r.returncode == 2


def test_setup_module_help():
    r = _run(["-m", "applybot.setup", "--help"])
    assert r.returncode == 0, r.stderr
    assert "--dry-run" in r.stdout
    assert "--no-browser" in r.stdout
    assert "--port" in r.stdout


def test_setup_module_dry_run():
    r = _run(["-m", "applybot.setup", "--dry-run"])
    assert r.returncode == 0, r.stderr
    assert "http://127.0.0.1:5000/" in r.stdout


def test_setup_module_dry_run_custom_port():
    r = _run(["-m", "applybot.setup", "--dry-run", "--port", "5010"])
    assert r.returncode == 0
    assert "5010" in r.stdout


@pytest.mark.skipif(
    not (ROOT / "config" / "secrets.py").is_file(),
    reason="Requires local config/secrets.py (not committed to git).",
)
def test_run_aibot_validate_config_when_secrets_present():
    r = _run([str(RUN_BOT), "--validate-config"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Configuration valid" in r.stdout
