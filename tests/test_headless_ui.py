"""APPLYBOT_HEADLESS_UI must short-circuit blocking prompts (E2E subprocesses)."""

from applybot.helpers import smart_alert, smart_confirm, smart_prompt


def test_headless_ui_confirm_returns_first_button(monkeypatch):
    monkeypatch.setenv("APPLYBOT_HEADLESS_UI", "1")
    assert smart_confirm("msg", buttons=["Yes", "No", "Maybe"]) == "Yes"


def test_headless_ui_alert_acknowledged(monkeypatch):
    monkeypatch.setenv("APPLYBOT_HEADLESS_UI", "1")
    assert smart_alert("body", title="T") is True


def test_headless_ui_prompt_default(monkeypatch):
    monkeypatch.setenv("APPLYBOT_HEADLESS_UI", "1")
    assert smart_prompt("?", default="fallback") == "fallback"
