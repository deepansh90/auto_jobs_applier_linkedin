"""
API-level tests for the small Flask UI (`app.py`).
Uses the Flask test client (no live network / browser).
"""

from __future__ import annotations

import csv
import importlib
from pathlib import Path


def _write_sample_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "Job ID": "job-1",
            "Title": "Engineer",
            "Company": "Acme",
            "HR Name": "Unknown",
            "HR Link": "",
            "Job Link": "https://example.com/j1",
            "External Job link": "https://ext.example/e1",
            "Date Applied": "Pending",
        }
    ]
    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def test_get_applied_jobs_404(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app = importlib.import_module("app")
    importlib.reload(app)
    c = app.app.test_client()
    r = c.get("/applied-jobs")
    assert r.status_code == 404


def test_get_applied_jobs_ok(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    excel = tmp_path / "all excels"
    _write_sample_csv(excel / "all_applied_applications_history.csv")
    app = importlib.import_module("app")
    importlib.reload(app)
    c = app.app.test_client()
    r = c.get("/applied-jobs")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 1
    assert data[0]["Job_ID"] == "job-1"


def test_put_updates_date_applied(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    excel = tmp_path / "all excels"
    csv_path = excel / "all_applied_applications_history.csv"
    _write_sample_csv(csv_path)
    app = importlib.import_module("app")
    importlib.reload(app)
    c = app.app.test_client()
    r = c.put("/applied-jobs/job-1")
    assert r.status_code == 200
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["Job ID"] == "job-1"
    assert rows[0]["Date Applied"] != "Pending"


def test_put_missing_job_returns_404(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    excel = tmp_path / "all excels"
    _write_sample_csv(excel / "all_applied_applications_history.csv")
    app = importlib.import_module("app")
    importlib.reload(app)
    c = app.app.test_client()
    r = c.put("/applied-jobs/does-not-exist")
    assert r.status_code == 404
