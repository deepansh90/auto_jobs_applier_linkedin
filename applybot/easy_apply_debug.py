"""
Optional Easy Apply diagnostics (e.g. E2E): snapshot visible form controls before final submit.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select


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


def collect_easy_apply_modal_fields(modal: WebElement) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
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
    return out


def append_pre_submit_dump_jsonl(
    path: str,
    modal: WebElement | None,
    job_id: str,
    job_link: str,
) -> None:
    """Append one JSON object per line (UTF-8). Creates parent directories if needed."""
    fields: list[dict[str, Any]] = []
    if modal is not None:
        try:
            fields = collect_easy_apply_modal_fields(modal)
        except Exception as e:
            fields = [{"error": str(e)}]
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "job_id": job_id,
        "job_link": job_link,
        "fields": fields,
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
