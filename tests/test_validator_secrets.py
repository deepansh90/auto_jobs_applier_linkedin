"""`validate_secrets` behavior for AI on vs off."""

from __future__ import annotations

import pytest

from applybot.validator import validate_secrets


def test_validate_secrets_skips_llm_when_use_ai_false(monkeypatch: pytest.MonkeyPatch) -> None:
    import config.secrets as sec

    monkeypatch.setattr(sec, "username", "user@example.com", raising=False)
    monkeypatch.setattr(sec, "password", "password123", raising=False)
    monkeypatch.setattr(sec, "use_AI", False, raising=False)
    monkeypatch.setattr(sec, "stream_output", False, raising=False)
    monkeypatch.setattr(sec, "llm_api_url", "", raising=False)
    monkeypatch.setattr(sec, "llm_api_key", "", raising=False)
    monkeypatch.setattr(sec, "ai_provider", "gemini", raising=False)
    monkeypatch.setattr(sec, "llm_model", "", raising=False)
    validate_secrets()


def test_validate_secrets_requires_llm_when_use_ai_true(monkeypatch: pytest.MonkeyPatch) -> None:
    import config.secrets as sec

    monkeypatch.setattr(sec, "username", "user@example.com", raising=False)
    monkeypatch.setattr(sec, "password", "password123", raising=False)
    monkeypatch.setattr(sec, "use_AI", True, raising=False)
    monkeypatch.setattr(sec, "stream_output", False, raising=False)
    monkeypatch.setattr(sec, "llm_api_url", "", raising=False)
    monkeypatch.setattr(sec, "llm_api_key", "", raising=False)
    monkeypatch.setattr(sec, "ai_provider", "gemini", raising=False)
    monkeypatch.setattr(sec, "llm_model", "m", raising=False)
    with pytest.raises(ValueError, match="llm_api_url"):
        validate_secrets()
