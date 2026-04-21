"""
Small Flask API over the applied-jobs CSV (legacy `all excels/` path or `history/`).

Served from repo root; used by tests and optional local dashboards.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify

LEGACY_CSV = Path("all excels") / "all_applied_applications_history.csv"
HISTORY_CSV = Path("history") / "applications.csv"

app = Flask(__name__)


def _resolved_csv_path() -> Path | None:
    if LEGACY_CSV.is_file():
        return LEGACY_CSV
    if HISTORY_CSV.is_file():
        return HISTORY_CSV
    return None


def _row_to_api_dict(row: dict[str, str]) -> dict[str, str]:
    return {k.replace(" ", "_"): (v or "") for k, v in row.items()}


@app.get("/applied-jobs")
def get_applied_jobs():
    path = _resolved_csv_path()
    if path is None:
        return "", 404
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return jsonify([_row_to_api_dict(r) for r in rows])


@app.put("/applied-jobs/<job_id>")
def put_applied_job(job_id: str):
    path = _resolved_csv_path()
    if path is None:
        return "", 404
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []
    if not fieldnames:
        return jsonify({"error": "empty csv"}), 400
    found = False
    stamp = datetime.now().isoformat(timespec="seconds")
    for r in rows:
        if (r.get("Job ID") or "").strip() == job_id:
            found = True
            if "Date Applied" in r:
                r["Date Applied"] = stamp
            break
    if not found:
        return "", 404
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return jsonify({"status": "ok", "Job_ID": job_id})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False)
