"""Gemini client module should not import deprecated `google.generativeai` at import time."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_gemini_connections_lazy_import_subprocess() -> None:
    code = (
        "import sys; "
        "import applybot.ai.geminiConnections; "
        "assert 'google.generativeai' not in sys.modules"
    )
    r = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stdout + r.stderr
