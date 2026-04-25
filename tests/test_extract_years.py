"""extract_years_of_experience ceiling logic (imports applybot.__main__)."""

from __future__ import annotations

import applybot.__main__ as m


def test_extract_years_respects_current_experience_ceiling(monkeypatch) -> None:
    monkeypatch.setattr(m, "current_experience", 15)
    text = "Looking for 15+ years of experience."
    assert m.extract_years_of_experience(text) == 15


def test_extract_years_excludes_above_ceiling(monkeypatch) -> None:
    monkeypatch.setattr(m, "current_experience", 15)
    text = "Must have 25+ years of experience."
    assert m.extract_years_of_experience(text) == 0


def test_extract_years_default_cap_when_not_set(monkeypatch) -> None:
    monkeypatch.setattr(m, "current_experience", -1)
    text = "Minimum 8 years experience."
    assert m.extract_years_of_experience(text) == 8
