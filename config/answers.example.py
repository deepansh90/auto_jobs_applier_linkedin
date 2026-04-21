"""
answers.py — rare and subjective questions that cannot be inferred from your resume.

Copy this file to `config/answers.py` and customize. Only a handful of values are
strictly needed; everything else has sensible defaults and is optional.

This file is gitignored.
"""

# ---- Money & notice (usually company-specific, required by many forms) ----
desired_salary = 0          # e.g. 120000 (USD) or 2400000 (INR). No quotes.
current_ctc = 0             # Your current CTC / base salary (numbers only).
notice_period = 30          # Days. 0 / 7 / 15 / 30 / 60 / 90.

# ---- Work auth ----
require_visa = "No"          # "Yes" or "No"
us_citizenship = "Other"     # See options in docs/CONFIGURE.md. Use "Other" outside US.

# ---- US Equal-opportunity (leave "" to not answer; required by some forms) ----
ethnicity = ""               # "Asian" / "Hispanic/Latino" / "White" / "Decline" / ""
gender = ""                  # "Male" / "Female" / "Decline" / ""
disability_status = ""       # "Yes" / "No" / "Decline" / ""
veteran_status = ""          # "Yes" / "No" / "Decline" / ""

# ---- Free-text (optional; profile.json summary is used if left empty) ----
cover_letter = ""
confidence_level = "8"       # 1-10, as a string. Used for "rate yourself" questions.

# ---- Behaviour toggles ----
pause_before_submit = False       # Pause for manual review before submit.
pause_at_failed_question = False  # Pause when the bot can't answer (else random).
overwrite_previous_answers = False
