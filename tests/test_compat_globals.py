"""Guards for config/_compat helpers used by applybot.__main__."""

from __future__ import annotations

from applybot.validator import check_boolean
from config._compat import ensure_linked_in_url_global


def test_ensure_linked_in_url_global_adds_key_when_absent() -> None:
    g: dict = {"other": 1}
    ensure_linked_in_url_global(g)
    assert "linkedIn" in g
    assert isinstance(g["linkedIn"], str)


def test_ensure_linked_in_url_global_noop_when_present() -> None:
    g = {"linkedIn": "https://www.linkedin.com/in/example"}
    ensure_linked_in_url_global(g)
    assert g["linkedIn"] == "https://www.linkedin.com/in/example"


def test_check_boolean_rejects_int_one() -> None:
    import pytest

    with pytest.raises(ValueError):
        check_boolean(1, "flag")  # noqa: FBT003 — intentional bad value
