# ApplyBot — LinkedIn Easy Apply

**Start here (new users)**

### 0. Prerequisites (browser)

The bot drives **Chromium** or **Google Chrome**.

- **Windows (PowerShell, Chromium via winget):**  
  `winget install Hibbiki.Chromium --accept-source-agreements --accept-package-agreements`
- **macOS:**  
  `brew install --cask chromium`
- **Linux (Debian/Ubuntu):**  
  `sudo apt update && sudo apt install chromium-browser -y`

More detail (Windows venv paths, etc.): **[docs/RUN.md](docs/RUN.md)**.

### 1. Install

From the repo root:

```bash
cd linkedin_easy_auto_applier_agent
python3 -m venv venv
./venv/bin/python -m pip install -U pip
./venv/bin/python -m pip install -r requirements.txt
```

On Windows after `python -m venv venv`, use `venv\Scripts\python.exe` instead of `./venv/bin/python` for the same commands.

### 2. Configure

**Recommended:** run the setup wizard. Your browser should open **http://127.0.0.1:5000/** automatically; if it does not, open that URL yourself, complete the form, and save.

```bash
./venv/bin/python -m applybot.setup
```

**Without the wizard:** copy each example **once** (skip a `cp` if you already have that file and only need to edit it). Put **`resume.pdf`** at the repo root or set `default_resume_path` in `config/questions.py`.

```bash
cp config/secrets.example.py config/secrets.py
cp config/personals.example.py config/personals.py
cp config/questions.example.py config/questions.py
cp config/answers.example.py config/answers.py
./venv/bin/python runAiBot.py --validate-config
```

**Do not** re-run `cp config/secrets.example.py config/secrets.py` after you have real LinkedIn credentials — it will overwrite them with placeholders. After the wizard, still review **`config/personals.py`** (address, EEO) and **`config/answers.py`** (salary, visa, notice) so submissions match you.

Minimum you must fill: **LinkedIn** email/password in `secrets.py`; **name, phone, address, EEO fields** in `personals.py`; **resume path** and **LinkedIn profile URL** in `questions.py`; **search terms** in `config/search.py`. Details and enums: **[docs/CONFIGURE.md](docs/CONFIGURE.md)**.

### 3. Run Easy Apply

After configuration (wizard or manual), start the bot:

```bash
./venv/bin/python runAiBot.py
```

That opens Chrome/Chromium and applies using `config/`. Login, logs, filters, and CLI flags: **[docs/RUN.md](docs/RUN.md)**. Optional live LinkedIn regression (pytest, pre-submit dumps): **[docs/RUN.md §7](docs/RUN.md#7-live-e2e-optional-regression)**.

---

**Heads up:** `config/secrets.py` is gitignored — do not commit it. Automating LinkedIn may violate their ToS; use at your own risk.
