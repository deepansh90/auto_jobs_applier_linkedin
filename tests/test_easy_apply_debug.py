"""Smoke tests for pre-submit JSONL dump helper."""

from __future__ import annotations

import json
from pathlib import Path

from applybot.easy_apply_debug import (
    append_pre_submit_dump_jsonl,
    append_submitted_qa_jsonl,
    questions_list_to_snapshot,
)


def test_append_pre_submit_dump_jsonl_modal_none(tmp_path: Path) -> None:
    path = str(tmp_path / "d.jsonl")
    append_pre_submit_dump_jsonl(path, None, "123", "https://www.linkedin.com/jobs/view/123")
    text = Path(path).read_text(encoding="utf-8")
    rec = json.loads(text.strip())
    assert rec["job_id"] == "123"
    assert rec["job_link"].endswith("/123")
    assert rec["fields"] == []


def test_questions_list_to_snapshot_normalizes_tuples() -> None:
    raw = {("Email", "a@b.com", "text", ""), ("City", "NYC", "text", "")}
    snap = questions_list_to_snapshot(raw)
    assert len(snap) == 2
    labels = {r["label"] for r in snap}
    assert labels == {"Email", "City"}


def test_append_pre_submit_dump_includes_questions(tmp_path: Path) -> None:
    path = str(tmp_path / "q.jsonl")
    snap = [{"label": "x", "value": "y", "kind": "text", "prev": ""}]
    append_pre_submit_dump_jsonl(
        path, None, "1", "https://example.com/jobs/1", questions_snapshot=snap
    )
    rec = json.loads(Path(path).read_text(encoding="utf-8").strip())
    assert rec["questions"] == snap


def test_append_submitted_qa_jsonl(tmp_path: Path) -> None:
    path = str(tmp_path / "qa.jsonl")
    snap = [{"label": "a", "value": "b", "kind": "text", "prev": ""}]
    append_submitted_qa_jsonl(path, "9", "https://example.com/9", snap)
    rec = json.loads(Path(path).read_text(encoding="utf-8").strip())
    assert rec["job_id"] == "9"
    assert rec["questions"] == snap
    assert "fields" not in rec
