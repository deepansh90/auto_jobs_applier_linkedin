from applybot.__main__ import _label_looks_skill_specific_years

tests = [
    "how many years of work experience do you have with mulesoft cloudhub?", # Should be True (with skill)
    "work experience (in years)?", # Should be False (ignore '(in years)')
    "how many years of experience do you have in temenos t24 ?", # Should be True (in skill)
    "how many years of experience do you have with python?", # Should be True (with skill)
    "total work experience", # Should be False (total)
    "relevant experience", # Should be False (relevant)
    "how many years of experience do you have in quality assurance/test engineer ?", # Should be True (in skill)
    "how many years of experience do you have (optional)?", # Should be False
]

for t in tests:
    print(f"'{t}': {_label_looks_skill_specific_years(t.lower())}")
