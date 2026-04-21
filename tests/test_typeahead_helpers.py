"""Unit tests for Easy Apply location typeahead ranking (no browser)."""

from applybot.typeahead_helpers import pick_best_typeahead_index, score_typeahead_option


def test_prefers_full_noida_over_greater_noida():
    opts = [
        "Greater Noida, Sadar, Uttar Pradesh, India",
        "Noida, Uttar Pradesh, India",
        "Noida Extension, Dadri, Uttar Pradesh, India",
    ]
    i = pick_best_typeahead_index("Noida", opts)
    assert i == 1
    assert opts[i].startswith("Noida,")


def test_prefers_canonical_when_typed_full_line():
    typed = "Noida, Uttar Pradesh, India"
    opts = ["Noida, Uttar Pradesh, India", "Greater Noida, Sadar, Uttar Pradesh, India"]
    assert pick_best_typeahead_index(typed, opts) == 0


def test_score_exact_match_wins():
    assert score_typeahead_option("Noida, UP, India", "Noida, UP, India") > score_typeahead_option(
        "Noida", "Greater Noida, X"
    )
