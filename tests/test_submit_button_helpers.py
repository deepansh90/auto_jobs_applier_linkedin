"""Unit tests for Easy Apply submit-button text heuristics."""

from applybot.submit_button_helpers import button_text_suggests_final_submit


def test_accepts_submit_application_phrases() -> None:
    assert button_text_suggests_final_submit("Submit application", "")
    assert button_text_suggests_final_submit("", "Submit your application")
    assert button_text_suggests_final_submit("Send application", "")


def test_rejects_review_next() -> None:
    assert not button_text_suggests_final_submit("Review", "")
    assert not button_text_suggests_final_submit("Next", "Continue to next step")


def test_short_labels() -> None:
    assert button_text_suggests_final_submit("Submit", "")
    assert button_text_suggests_final_submit("Done", "")
