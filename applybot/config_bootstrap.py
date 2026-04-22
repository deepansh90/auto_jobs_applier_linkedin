"""
Early checks before importing `applybot.__main__` or `applybot.validator` (which pull `config.secrets`).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def require_secrets_file(repo_root: Path | None = None) -> None:
    """
    Exit with code 2 and a short message if `config/secrets.py` is missing.

    `repo_root` defaults to this package's parent (the repo). Tests may pass a temp tree.
    """
    root = repo_root or _REPO_ROOT
    path = root / "config" / "secrets.py"
    if path.is_file():
        return
    print(
        f"Missing required file: {path}\n\n"
        "Create it from the example, then edit credentials (and API keys if using AI):\n"
        f"  cp config/secrets.example.py config/secrets.py\n\n"
        "Or run the setup wizard from the repo root:\n"
        f"  ./venv/bin/python -m applybot.setup\n",
        file=sys.stderr,
    )
    raise SystemExit(2)
