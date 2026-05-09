"""
Pure helpers for detecting LinkedIn Easy Apply *final* submit actions.

Kept separate from Selenium so unit tests do not need a browser.
"""


def button_text_suggests_final_submit(visible_text: str, aria_label: str) -> bool:
    """
    Return True when combined visible text + aria-label looks like a final
    submit / confirm action (not e.g. "Next" or "Review").
    """
    combined = f"{visible_text or ''} {aria_label or ''}".lower()
    c = combined.strip()
    if not c:
        return False
    phrases = (
        "submit application",
        "submit your application",
        "send application",
        "submit my application",
        "confirm application",
        "post application",
        "apply now",
    )
    for p in phrases:
        if p in c:
            return True
    # Short primary-button labels on the last step
    if c in ("submit", "done", "post", "confirm", "send"):
        return True
    return False
