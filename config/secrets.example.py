# config/secrets.py (EXAMPLE)
#
# Copy this file to `secrets.py` and fill in YOUR real credentials.
# `secrets.py` is gitignored so credentials never get committed.
#
# Safer: set LI_USERNAME / LI_PASSWORD (and API keys) in the environment and
# leave placeholders below, so exports and screen shares never embed secrets.

import os

# --- LinkedIn credentials ---
username = os.environ.get("LI_USERNAME", "<LINKEDIN_EMAIL_OR_USERNAME>")
password = os.environ.get("LI_PASSWORD", "<LINKEDIN_PASSWORD>")

# --- AI Configuration ---
use_AI = True
ai_provider = "gemini"  # Primary provider: "gemini" or "openai"

# 1. Google Gemini Settings (Recommended - has generous free tier)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "<YOUR_GEMINI_API_KEY>")  # https://aistudio.google.com/app/apikey
GEMINI_MODEL = "gemini-2.0-flash-lite"

# 2. OpenAI Settings (Failover)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "<YOUR_OPENAI_API_KEY>")
OPENAI_API_URL = "https://api.openai.com/v1"
OPENAI_MODEL = "gpt-4o"

# Legacy / Global settings (kept for backward compatibility)
llm_api_key = GEMINI_API_KEY
llm_api_url = "https://generativelanguage.googleapis.com/v1beta"
llm_model = GEMINI_MODEL
llm_spec = "gemini"

stream_output = False
showAiErrorAlerts = True
