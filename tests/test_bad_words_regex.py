"""Word-boundary bad_words matching (mirrors get_job_description logic)."""

from __future__ import annotations

import re


def _matches_bad_word(job_low: str, word: str) -> bool:
    w = (word or "").strip()
    if not w:
        return False
    wl = w.lower()
    if re.match(r"^[^\w]", wl):
        pat = re.compile(r"(?<!\w)" + re.escape(wl) + r"(?!\w)")
    else:
        pat = re.compile(r"\b" + re.escape(wl) + r"\b")
    return bool(pat.search(job_low))


def test_dotnet_does_not_match_internet() -> None:
    job = "We build internet-scale products.".lower()
    assert not _matches_bad_word(job, ".NET")


def test_dotnet_matches_standalone() -> None:
    job = "Strong .NET and C# required.".lower()
    assert _matches_bad_word(job, ".NET")
