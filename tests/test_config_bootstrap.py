"""Tests for early `config/secrets.py` presence check."""

from __future__ import annotations

import io
from contextlib import redirect_stderr
from pathlib import Path

import pytest

from applybot.config_bootstrap import require_secrets_file


def test_require_secrets_file_exits_when_missing(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    with redirect_stderr(buf), pytest.raises(SystemExit) as ei:
        require_secrets_file(tmp_path)
    assert ei.value.code == 2
    err = buf.getvalue()
    assert "secrets.py" in err
    assert "secrets.example.py" in err


def test_require_secrets_file_ok_when_present(tmp_path: Path) -> None:
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "secrets.py").write_text("# test stub\n", encoding="utf-8")
    require_secrets_file(tmp_path)
