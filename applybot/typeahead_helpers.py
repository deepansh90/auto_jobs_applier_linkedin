"""
Pure helpers for LinkedIn / partner Easy Apply location typeaheads.

Used by applybot.__main__.commit_typeahead_choice and covered by unit tests
so ranking stays stable when LinkedIn tweaks DOM classes.
"""

from __future__ import annotations


def _first_csv_segment(text: str) -> str:
    return text.split(",")[0].strip().lower()


def score_typeahead_option(typed_raw: str, option_text: str) -> tuple[int, int]:
    """
    Higher tuple sorts better. Primary rewards exact city matches over
    "Greater Noida" / "Noida Extension" when the user typed a short city.
    """
    typed = typed_raw.strip().lower()
    opt = option_text.strip().lower()
    if not typed or not opt:
        return (-1, 0)
    if opt == typed:
        return (100, 0)

    typed_head = _first_csv_segment(typed)
    opt_head = _first_csv_segment(opt)

    # Strong: first segment matches (e.g. typed "Noida" vs "Noida, Uttar Pradesh, India")
    if opt_head == typed_head:
        return (85, -len(opt))

    # Typed is a prefix of a longer canonical line
    if opt.startswith(typed + ",") or opt.startswith(typed + " "):
        return (80, -len(opt))

    # Penalize "Greater Noida" when user meant plain "Noida"
    if typed_head == "noida" and "greater" in opt_head and "noida" in opt_head:
        return (15, 0)

    # Other extensions that share the token but are not the core city
    if typed_head and opt_head != typed_head and typed_head in opt_head and len(opt_head) > len(typed_head) + 2:
        return (35, -len(opt))

    if opt.startswith(typed):
        return (60, -len(opt))
    if typed_head and typed_head in opt:
        return (40, 0)
    return (0, 0)


def pick_best_typeahead_index(typed_raw: str, option_texts: list[str]) -> int:
    """Return index of best option, or 0 if list empty."""
    if not option_texts:
        return 0
    best_i = 0
    best_key = score_typeahead_option(typed_raw, option_texts[0])
    for i, txt in enumerate(option_texts[1:], start=1):
        key = score_typeahead_option(typed_raw, txt)
        if key > best_key:
            best_key = key
            best_i = i
    return best_i
