# auto_jobs_applier_linkedin

An automated LinkedIn Easy Apply agent that handles the entire application process seamlessly.

## What it does

- **Automated Searching** — Uses precise search URLs (`f_EA=true`) to discover Easy Apply jobs matching your criteria.
- **Smart Form Filling** — Answers complex multi-step application questions dynamically using a Gemini/OpenAI failover dispatcher.
- **Offline Resilience** — Safely falls back to your static configuration values if AI providers hit rate-limits or are unavailable.
- **Persistent Sessions** — Operates on a persistent local Chrome profile to eliminate repetitive CAPTCHAs and login prompts.

## Get running in 60 seconds

### Path A: Setup Wizard (Recommended)
Launch the frictionless Local UI to establish your baseline details in seconds.
```bash
git clone https://github.com/deepansh90/auto_jobs_applier_linkedin.git
cd auto_jobs_applier_linkedin
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Launch the Setup Wizard UI
python -m applybot.setup

# Start the bot
python -m applybot
```

### Path B: Manual Configuration (Power Users)
If you prefer raw configuration without the Setup UI, you can populate the Python settings files manually.
```bash
cp config/secrets.example.py config/secrets.py && $EDITOR config/secrets.py
# (See docs/CONFIGURE.md for other configurations)
python runAiBot.py
```

> **Note:** For advanced filtering, custom question answering, and a first-run checklist, see our comprehensive [Configuration Guide](docs/CONFIGURE.md).

## Safety and Privacy

- **Never commit your configuration** (`config/secrets.py`, `config/user.settings.json`, resume, etc.). They are natively ignored by git to protect you.
- **LinkedIn Credentials are localized.** Passwords and keys exist only on your host machine.
- **AI Analytics.** Utilizing the Gemini/OpenAI dispatcher involves sending snippets of your resume and parsed job applications out continuously.
- **ToS Warning.** Automated interaction with LinkedIn violates their Terms of Service. Use strictly at your own discretion.
