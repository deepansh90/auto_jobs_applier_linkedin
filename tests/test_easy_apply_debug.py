"""Smoke tests for pre-submit JSONL dump helper."""

from __future__ import annotations

import json
from pathlib import Path

from applybot.easy_apply_debug import append_pre_submit_dump_jsonl


def test_append_pre_submit_dump_jsonl_modal_none(tmp_path: Path) -> None:
    path = str(tmp_path / "d.jsonl")
    append_pre_submit_dump_jsonl(path, None, "123", "https://www.linkedin.com/jobs/view/123")
    text = Path(path).read_text(encoding="utf-8")
    rec = json.loads(text.strip())
    assert rec["job_id"] == "123"
    assert rec["job_link"].endswith("/123")
    assert rec["fields"] == []
