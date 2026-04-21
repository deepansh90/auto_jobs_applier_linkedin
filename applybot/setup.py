import os
import json
import argparse
import secrets
import threading
import time
import webbrowser
from flask import Flask, render_template_string, request, jsonify

# Import the auto-extraction logic
# Note: This is inside applybot package, so we use absolute import
from applybot.resume_autofill import ensure_profile

app = Flask(__name__)

# LinkedIn Branded Template
TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ApplyBot | Setup</title>
    <style>
        :root {
            --li-blue: #0A66C2;
            --li-blue-hover: #004182;
            --li-bg: #F3F2EF;
            --li-text: rgba(0,0,0,0.9);
            --li-secondary-text: rgba(0,0,0,0.6);
            --li-white: #FFFFFF;
            --li-border: #dce6e9;
        }
        body {
            font-family: -apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", "Fira Sans", Ubuntu, Oxygen, "Oxygen Sans", Cantarell, "Droid Sans", "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Lucida Grande", Helvetica, Arial, sans-serif;
            margin: 0;
            background-color: var(--li-bg);
            color: var(--li-text);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .card {
            background-color: var(--li-white);
            border-radius: 8px;
            box-shadow: 0 0 0 1px rgba(0,0,0,0.08), 0 4px 4px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 480px;
            padding: 32px;
            transition: all 0.3s ease;
        }
        .header {
            text-align: center;
            margin-bottom: 24px;
        }
        .logo {
            font-size: 24px;
            font-weight: 700;
            color: var(--li-blue);
            text-decoration: none;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
        }
        .logo span {
            background: var(--li-blue);
            color: white;
            padding: 0 4px;
            border-radius: 2px;
        }
        h1 {
            font-size: 24px;
            font-weight: 400;
            margin: 8px 0;
        }
        p.subtitle {
            color: var(--li-secondary-text);
            font-size: 14px;
            margin-top: 0;
        }
        .step { display: none; }
        .step.active { display: block; animation: slideIn 0.3s ease-out; }
        @keyframes slideIn { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }
        
        .form-group { margin-bottom: 20px; text-align: left; }
        label {
            display: block;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        input {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid rgba(0,0,0,0.6);
            border-radius: 4px;
            font-size: 16px;
            box-sizing: border-box;
            transition: border 0.2s;
        }
        input:focus {
            outline: none;
            border: 2px solid var(--li-blue);
            padding: 9px 11px;
        }
        .btn {
            background-color: var(--li-blue);
            color: white;
            border: none;
            border-radius: 24px;
            padding: 12px 24px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            margin-top: 16px;
            transition: background-color 0.2s;
        }
        .btn:hover { background-color: var(--li-blue-hover); }
        .btn-secondary {
            background-color: transparent;
            color: var(--li-secondary-text);
            margin-top: 12px;
            font-size: 14px;
            text-decoration: underline;
            cursor: pointer;
            border: none;
            display: block;
            width: 100%;
        }
        .progress-bar {
            height: 4px;
            background: #ebebeb;
            border-radius: 2px;
            margin-bottom: 24px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: var(--li-blue);
            transition: width 0.3s;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <div class="logo">Apply<span>Bot</span></div>
            <h1 id="title">Build your career</h1>
            <p class="subtitle" id="subtitle">Stay updated on your professional world</p>
        </div>
        <div class="progress-bar"><div class="progress-fill" id="progress" style="width: 33%;"></div></div>

        <form id="setupForm">
            <!-- Step 1: Account -->
            <div id="step-1" class="step active">
                <div class="form-group">
                    <label>Email or phone</label>
                    <input type="text" id="li_username" placeholder="__PH_EMAIL__" required>
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="li_password" placeholder="__PH_PASS__" required>
                </div>
                <button type="button" class="btn" onclick="nextStep(2)">Agree & Join</button>
            </div>

            <!-- Step 2: Resume & AI -->
            <div id="step-2" class="step">
                <div class="form-group">
                    <label>Resume PDF path</label>
                    <input type="text" id="resume_path" placeholder="__PH_RESUME__" required>
                </div>
                <div class="form-group">
                    <label>Gemini API Key (Recommended)</label>
                    <input type="password" id="gemini_key" placeholder="__PH_GEM__">
                </div>
                <p style="font-size: 12px; color: var(--li-secondary-text);">Identity and experience details will be derived automatically from your resume.</p>
                <button type="button" class="btn" onclick="nextStep(3)">Continue</button>
                <button type="button" class="btn-secondary" onclick="nextStep(1)">Back</button>
            </div>

            <!-- Step 3: Preferences -->
            <div id="step-3" class="step">
                <div class="form-group">
                    <label>Job title keywords</label>
                    <input type="text" id="search_terms" placeholder="Lead Engineer, Staff Engineer" required>
                </div>
                <div class="form-group">
                    <label>Search Location</label>
                    <input type="text" id="search_location" placeholder="Noida" required>
                </div>
                <div class="form-group">
                    <label>Expected Salary (Annual)</label>
                    <input type="text" id="desired_salary" placeholder="7500000" required>
                </div>
                <div class="form-group" style="display: flex; align-items: center; gap: 8px;">
                    <input type="checkbox" id="follow_companies" style="width: auto; margin: 0;">
                    <label style="margin: 0; font-weight: 400; font-size: 14px;">Follow companies after applying</label>
                </div>
                <button type="button" class="btn" onclick="submitForm()">Complete Setup</button>
                <button type="button" class="btn-secondary" onclick="nextStep(2)">Back</button>
            </div>

            <div id="step-success" class="step" style="text-align:center;">
                <h2 style="color: var(--li-blue);">Account Setup Successful</h2>
                <p>Everything is ready. AI has been configured to derive details from your resume.</p>
                <div style="padding: 20px; font-family: monospace; background: #f8f8f8; border-radius: 4px; font-size: 13px; margin-bottom: 20px; line-height: 1.6;">
                    ./venv/bin/python runAiBot.py
                </div>
                <p style="font-size: 14px; color: var(--li-secondary-text);">Copy the command above, paste it into a terminal at the <strong>repo root</strong>, and press Enter. Open LinkedIn in your own browser when you want to browse jobs — the bot will sign in when it runs.</p>
                <!-- Disabled: in-browser LinkedIn (auto/tab open) — pop-up blockers and UX noise; keep CLI-only success for now.
                <p id="li-jobs-hint" style="font-size: 13px; color: var(--li-secondary-text); margin-top: 8px;">…</p>
                <button type="button" class="btn" id="btn-open-linkedin-jobs" onclick="window.open('https://www.linkedin.com/jobs/', '_blank', 'noopener,noreferrer');">Open LinkedIn Jobs</button>
                <p style="font-size: 12px; …"><a href="https://www.linkedin.com/jobs/" target="_blank" …>linkedin.com/jobs</a></p>
                -->
            </div>
        </form>
    </div>

    <script>
        function nextStep(step) {
            document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
            if (step === 'success') {
                document.getElementById('step-success').classList.add('active');
                document.getElementById('progress').style.width = '100%';
                document.getElementById('title').innerText = "All Done!";
                document.getElementById('subtitle').innerText = "Configuration saved successfully.";
                return;
            }
            document.getElementById(`step-${step}`).classList.add('active');
            
            const progress = (step / 3) * 100;
            document.getElementById('progress').style.width = progress + '%';
            
            if (step == 1) {
                document.getElementById('title').innerText = "Build your career";
                document.getElementById('subtitle').innerText = "Stay updated on your professional world";
            } else if (step == 2) {
                document.getElementById('title').innerText = "Tell us about you";
                document.getElementById('subtitle').innerText = "Personalizing your application experience";
            } else if (step == 3) {
                document.getElementById('title').innerText = "Search Preferences";
                document.getElementById('subtitle').innerText = "Where should we start applying?";
            }
        }

        async function submitForm() {
            const formData = {
                li_username: document.getElementById('li_username').value,
                li_password: document.getElementById('li_password').value,
                gemini_key: document.getElementById('gemini_key').value,
                search_terms: document.getElementById('search_terms').value,
                search_location: document.getElementById('search_location').value,
                resume_path: document.getElementById('resume_path').value,
                desired_salary: document.getElementById('desired_salary').value,
                follow_companies: document.getElementById('follow_companies').checked,
            };

            const resp = await fetch('/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (resp.ok) {
                nextStep('success');
                // Disabled: update #li-jobs-hint / LinkedIn tab open (see commented HTML in step-success).
            } else {
                const err = await resp.json();
                alert("Error: " + (err.error || "Failed to save configuration"));
            }
        }
    </script>
</body>
</html>
"""

def _inject_placeholder_examples(html: str) -> str:
    """Random-looking but fake placeholders so we never show one user's data to everyone."""
    ph_email = f"you.{secrets.token_hex(3)}@example.invalid"
    ph_pass = f"Ex_{secrets.token_hex(4)}!0"
    ph_resume = f"/Users/you/Documents/resume_{secrets.token_hex(2)}.pdf"
    ph_gem = f"AIza{secrets.token_hex(12)}…"
    return (
        html.replace("__PH_EMAIL__", ph_email)
        .replace("__PH_PASS__", ph_pass)
        .replace("__PH_RESUME__", ph_resume)
        .replace("__PH_GEM__", ph_gem)
    )


@app.route("/")
def home():
    return render_template_string(_inject_placeholder_examples(TEMPLATE))

@app.route("/submit", methods=["POST"])
def submit():
    data = request.json
    config_dir = "config"
    os.makedirs(config_dir, exist_ok=True)

    # 1. Generate secrets.py FIRST so extraction can use the key
    username_val = json.dumps(data.get("li_username", ""))
    password_val = json.dumps(data.get("li_password", ""))
    gemini_key_val = json.dumps(data.get("gemini_key", ""))

    secrets_content = f'''# config/secrets.py (Auto-generated by Setup)
username = {username_val}
password = {password_val}

use_AI = True
ai_provider = "gemini"

GEMINI_API_KEY = {gemini_key_val}
GEMINI_MODEL = "gemini-2.0-flash-lite"

# Legacy / Global settings
llm_api_key = GEMINI_API_KEY
llm_api_url = "https://generativelanguage.googleapis.com/v1beta"
llm_model = GEMINI_MODEL
llm_spec = "gemini"

stream_output = False
showAiErrorAlerts = True
'''
    with open(os.path.join(config_dir, "secrets.py"), "w", encoding="utf-8") as f:
        f.write(secrets_content)

    # 2. Trigger AI extraction immediately
    resume_path = data.get("resume_path", "")
    profile = {}
    if resume_path and os.path.exists(resume_path):
        # We ensure profile.json is created from the resume
        profile = ensure_profile(config_dir, resume_path)

    # 3. Parse search preferences
    search_terms = [t.strip() for t in data.get("search_terms", "").split(",") if t.strip()]
    if not search_terms:
        search_terms = ["Software Engineer"]
    
    try:
        salary_str = str(data.get("desired_salary", "7500000")).replace(",", "").strip()
        salary_val = int(salary_str) if salary_str else 0
    except ValueError:
        return jsonify({"status": "error", "error": "Invalid salary amount. Please enter a number."}), 400
        
    user_settings = {
        "search_terms": search_terms,
        "search_location": data.get("search_location", "Noida"),
        "default_resume_path": resume_path,
        "desired_salary": salary_val,
        "follow_companies": data.get("follow_companies", False)
    }

    with open(os.path.join(config_dir, "user.settings.json"), "w", encoding="utf-8") as f:
        json.dump(user_settings, f, indent=4)
        
    # Write success marker
    with open(os.path.join(config_dir, ".setup_complete"), "w", encoding="utf-8") as f:
        f.write("version: 1")

    return jsonify({"status": "success", "extracted": profile.get("name", "Unknown")})


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ApplyBot local web onboarding (LinkedIn-style setup wizard).",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address for the setup server (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="TCP port for the setup server (default: 5000).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the URL that would be served and exit without starting Flask (for CI/scripts).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open a browser (SSH/headless).",
    )
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}/"
    if args.dry_run:
        print(f"Dry run: onboarding UI would be served at {url}")
        return

    print("Welcome to ApplyBot Setup UI.")
    print(f"Serving {url}")
    if not args.no_browser and os.environ.get("APPLYBOT_SETUP_NO_BROWSER", "").strip() not in ("1", "true", "yes"):

        def _open_when_ready() -> None:
            time.sleep(1.2)
            try:
                webbrowser.open(url)
            except Exception as e:
                print(f"(Could not open browser automatically: {e})")

        threading.Thread(target=_open_when_ready, daemon=True).start()
    else:
        print(f"Open this URL in your browser: {url}")

    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
