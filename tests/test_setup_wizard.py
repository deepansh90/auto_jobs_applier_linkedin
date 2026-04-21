import os
import json
import pytest
from applybot.setup import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_setup_wizard_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"ApplyBot" in response.data
    assert b"Setup" in response.data
    assert b"li_username" in response.data
    body = response.data.decode("utf-8")
    assert "example.invalid" in body
    assert "bhadaks" not in body.lower()

def test_setup_wizard_submit(client, tmp_path, monkeypatch):
    # Sandbox the working directory to our tmp_path so 'config/' writes safely
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / "config"

    payload = {
        "li_username": "test@example.com",
        "li_password": "supersecretpassword",
        "gemini_key": "AIzaSyTestKey123",
        "search_terms": "Software Engineer, Manager",
        "search_location": "San Francisco, CA",
        "resume_path": "/test/resume.pdf"
    }

    response = client.post("/submit", json=payload)
    assert response.status_code == 200
    assert response.json["status"] == "success"

    # Verify user.settings.json
    settings_file = config_dir / "user.settings.json"
    assert settings_file.exists()
    with open(settings_file, "r") as f:
        settings = json.load(f)
        assert len(settings["search_terms"]) == 2
        assert settings["search_terms"][0] == "Software Engineer"
        assert settings["search_location"] == "San Francisco, CA"

    # Verify secrets.py
    secrets_file = config_dir / "secrets.py"
    assert secrets_file.exists()
    content = secrets_file.read_text()
    assert 'username = "test@example.com"' in content
    assert 'GEMINI_API_KEY = "AIzaSyTestKey123"' in content

    # Verify completion flag
    flag_file = config_dir / ".setup_complete"
    assert flag_file.exists()
    assert flag_file.read_text() == "version: 1"


def test_setup_wizard_submit_rejects_invalid_salary(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = {
        "li_username": "u@example.com",
        "li_password": "pw",
        "gemini_key": "",
        "search_terms": "Engineer",
        "search_location": "Noida",
        "resume_path": "",
        "desired_salary": "not-a-number",
    }
    response = client.post("/submit", json=payload)
    assert response.status_code == 400
    body = response.get_json()
    assert body.get("status") == "error"
    assert "salary" in (body.get("error") or "").lower()


def test_setup_wizard_secrets_use_python_repr_escaping(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / "config"
    payload = {
        "li_username": "user@test.com",
        "li_password": 'pass"with\'quotes',
        "gemini_key": "k",
        "search_terms": "Engineer",
        "search_location": "Noida",
        "resume_path": "",
    }
    response = client.post("/submit", json=payload)
    assert response.status_code == 200
    content = (config_dir / "secrets.py").read_text()
    assert 'pass"with' in content or "pass\\\"with" in content
    # json.dumps in generated file: safe repr, file must remain importable
    ns: dict = {}
    exec(compile(content, str(config_dir / "secrets.py"), "exec"), ns, ns)
    assert ns["username"] == "user@test.com"
    assert ns["password"] == 'pass"with\'quotes'
