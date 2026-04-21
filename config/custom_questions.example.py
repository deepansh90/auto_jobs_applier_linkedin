# >>>>>>>>>>> Custom Questions & Answers <<<<<<<<<<<
#
# Copy this file to `custom_questions.py` and customize with YOUR own answers.
# `custom_questions.py` is gitignored so your personal data never gets committed.
#
# Map keywords (case-insensitive) to specific answers.
# The bot will search for these keywords in the question label.
# Priority: Custom Keywords > Default Config (config/questions.py) > AI/Random

custom_answers = {
    # Technical Skills - Years of Experience (examples; edit to match YOUR experience)
    "python": "<YEARS>",
    "java": "<YEARS>",
    "aws": "<YEARS>",
    "llm": "<YEARS>",
    "generative ai": "<YEARS>",
    "distributed systems": "<YEARS>",

    # Personal Info & Contact
    "first name": "<FIRST_NAME>",
    "last name": "<LAST_NAME>",
    "mobile phone number": "<PHONE_NUMBER>",
    "email address": "<EMAIL>",
    "city": "<CITY>",
    "location (city)": "<CITY>",
    "location": "<CITY>, <COUNTRY>",
    "phone country code": "<COUNTRY_CODE>",   # e.g. "+1", "+91"
    "linkedin": "<LINKEDIN_URL>",

    # Salary & Logistics
    "expected in-hand salary": "<EXPECTED_SALARY>",
    "current in hand salary": "<CURRENT_SALARY>",
    "relocate": "Yes",
    "willing to work from office": "Yes",
    "onsite": "Yes",
    "hybrid": "Yes",

    # Employer-specific compliance questions (add your own as you encounter them)
    # "Do you anticipate needing <Company> to sponsor your work authorization...": "No",
    # "Have you applied to <Company> in the past 6 months": "No",
}

# Note: For numeric questions, keep the value in quotes if it's a fixed string choice,
# or as a raw number/string as required by the LinkedIn form field.
