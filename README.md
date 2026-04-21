# ApplyBot — LinkedIn Easy Apply

**Start here (new users)**

```bash
cd linkedin_easy_auto_applier_agent
python3 -m venv venv
./venv/bin/python -m pip install -U pip
./venv/bin/python -m pip install -r requirements.txt
./venv/bin/python -m applybot.setup
```

Your browser should open **http://127.0.0.1:5000/** automatically. If it does not, open that address yourself, finish the form, then run:

```bash
./venv/bin/python runAiBot.py
```

That opens Chrome/Chromium and applies using `config/` (credentials and search prefs come from the wizard). More detail, login, logs, and tests: **[docs/RUN.md](docs/RUN.md)**.

---

**Heads up:** `config/secrets.py` is gitignored — do not commit it. Automating LinkedIn may violate their ToS; use at your own risk.
