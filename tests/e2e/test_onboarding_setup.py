"""
HTTP E2E for the ApplyBot onboarding wizard (Flask setup UI).

No browser or LinkedIn session required. Complements tests/test_setup_wizard.py
and the live LinkedIn marker ``e2e``.
"""

from __future__ import annotations

import json
import os

import pytest

from applybot.setup import app

pytestmark = pytest.mark.onboarding


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_onboarding_home_includes_success_cli_flow(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.data.decode("utf-8")
    assert "runAiBot.py" in body
    assert "Account Setup Successful" in body
    assert "submitForm" in body


def test_onboarding_submit_end_to_end_writes_config(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / "config"

    payload = {
        "li_username": "onboard-e2e@example.com",
        "li_password": "onboard-e2e-secret",
        "gemini_key": "AIzaOnboardE2E",
        "search_terms": "Engineer, Lead",
        "search_location": "Remote",
        "resume_path": "",
        "desired_salary": "8000000",
        "follow_companies": False,
    }
    r = client.post("/submit", json=payload)
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("status") == "success"

    settings = json.loads((config_dir / "user.settings.json").read_text(encoding="utf-8"))
    assert settings["search_location"] == "Remote"
    assert settings["search_terms"] == ["Engineer", "Lead"]
    assert settings["desired_salary"] == 8000000

    secrets_text = (config_dir / "secrets.py").read_text(encoding="utf-8")
    assert 'onboard-e2e@example.com' in secrets_text
    assert (config_dir / ".setup_complete").read_text(encoding="utf-8").strip() == "version: 1"


def test_onboarding_submit_without_desired_salary_defaults(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / "config"
    payload = {
        "li_username": "u2@example.com",
        "li_password": "pw2",
        "gemini_key": "",
        "search_terms": "QA",
        "search_location": "Berlin",
        "resume_path": "",
    }
    r = client.post("/submit", json=payload)
    assert r.status_code == 200
    settings = json.loads((config_dir / "user.settings.json").read_text(encoding="utf-8"))
    assert settings["desired_salary"] == 7500000
