"""
Entry point for LinkedIn Easy Apply runs.

Supports `--help` without importing the Selenium stack, and `--validate-config`
using only the validator (still loads `config/*`).
"""

from __future__ import annotations

import sys

_CLI_HELP = """usage: python runAiBot.py [options]

Run the LinkedIn Easy Apply bot: opens the browser, searches jobs (see
config/search.py), and submits applications until max_applied_jobs (see
config/settings.py).

optional arguments:
  -h, --help          Show this message and exit.
  --validate-config   Load config/*.py, run validation, and exit (no browser).

Environment (Easy Apply run):
  MAX_APPLIED_JOBS     Cap successful submissions (overrides config/settings.py for this process).
  APPLYBOT_HEADLESS_UI When set to 1, skip blocking alert/confirm dialogs (for E2E subprocesses).

Examples:
  python runAiBot.py
  python runAiBot.py --validate-config

Onboarding (first-time credentials and resume) is separate:
  ./venv/bin/python -m applybot.setup
    (tries to open http://127.0.0.1:5000/ in your default browser after the server starts)
"""


def main_cli() -> int:
    argv = sys.argv[1:]
    if not argv:
        from applybot.__main__ import main

        main()
        return 0
    if argv[0] in ("-h", "--help"):
        print(_CLI_HELP.strip())
        return 0
    if argv[0] == "--validate-config":
        from applybot.validator import validate_config

        validate_config()
        print("Configuration valid.")
        return 0
    print(f"Unknown option: {argv[0]!r}\n", file=sys.stderr)
    print(_CLI_HELP.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main_cli())
