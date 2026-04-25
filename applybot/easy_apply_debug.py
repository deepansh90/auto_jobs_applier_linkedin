"""
Optional Easy Apply diagnostics (e.g. E2E): snapshot visible form controls before final submit.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select

_MODAL_FIELD_CSS = ".jobs-easy-apply-modal input, .jobs-easy-apply-modal textarea, .jobs-easy-apply-modal select"
_ARTDECO_MODAL_FIELD_CSS = ".artdeco-modal input, .artdeco-modal textarea, .artdeco-modal select"


def _field_dict(el: WebElement) -> dict[str, Any]:
    tag = el.tag_name.lower()
    d: dict[str, Any] = {"tag": tag}
    for attr in ("name", "id", "type", "aria-label", "placeholder", "role"):
        try:
            v = el.get_attribute(attr)
            if v:
                d[attr] = v
        except Exception:
            pass
    try:
        d["displayed"] = bool(el.is_displayed())
    except Exception:
        d["displayed"] = False
    try:
        if tag == "select":
            sel = Select(el)
            opts = [o.text for o in sel.all_selected_options]
            d["value"] = " | ".join(opts) if opts else ""
        else:
            d["value"] = el.get_attribute("value") or ""
    except Exception:
        d["value"] = ""
    return d


def collect_easy_apply_modal_fields(
    modal: WebElement | None,
    driver: WebDriver | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if modal is not None:
        for el in modal.find_elements(By.CSS_SELECTOR, "input, textarea, select"):
            try:
                if not el.is_displayed():
                    continue
            except Exception:
                continue
            try:
                out.append(_field_dict(el))
            except Exception:
                continue
    if not out and driver is not None:
        for css in (_MODAL_FIELD_CSS, _ARTDECO_MODAL_FIELD_CSS):
            for el in driver.find_elements(By.CSS_SELECTOR, css):
                try:
                    if not el.is_displayed():
                        continue
                except Exception:
                    continue
                try:
                    out.append(_field_dict(el))
                except Exception:
                    continue
            if out:
                break
    return out


def questions_list_to_snapshot(questions_list: Iterable[Any] | None) -> list[dict[str, Any]]:
    """Normalize fill_easy_apply_form ``questions_list`` entries to JSON-safe dicts."""
    rows: list[dict[str, Any]] = []
    for item in questions_list or ():
        if not item:
            continue
        if isinstance(item, (list, tuple)):
            lab = str(item[0]) if len(item) > 0 else ""
            val = str(item[1]) if len(item) > 1 else ""
            kind = str(item[2]) if len(item) > 2 else ""
            prev = str(item[3]) if len(item) > 3 else ""
            rows.append({"label": lab, "value": val, "kind": kind, "prev": prev})
    return rows


def append_pre_submit_dump_jsonl(
    path: str,
    modal: WebElement | None,
    job_id: str,
    job_link: str,
    questions_snapshot: list[dict[str, Any]] | None = None,
    driver: WebDriver | None = None,
) -> None:
    """Append one JSON object per line (UTF-8). Creates parent directories if needed."""
    fields: list[dict[str, Any]] = []
    if modal is not None or driver is not None:
        try:
            fields = collect_easy_apply_modal_fields(modal, driver=driver)
        except Exception as e:
            fields = [{"error": str(e)}]
    rec: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "job_id": job_id,
        "job_link": job_link,
        "fields": fields,
    }
    # Patch 2A: Annotate empty fields (review page has no editable inputs)
    if not fields:
        rec["fields_note"] = "review_page_no_inputs"
    if questions_snapshot is not None:
        rec["questions"] = questions_snapshot
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def append_submitted_qa_jsonl(
    path: str,
    job_id: str,
    job_link: str,
    questions_snapshot: list[dict[str, Any]],
) -> None:
    """Append one line: job id/link + questions only (no DOM)."""
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "job_id": job_id,
        "job_link": job_link,
        "questions": questions_snapshot,
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
