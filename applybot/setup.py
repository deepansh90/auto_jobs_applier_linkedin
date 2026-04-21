import os
import json
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Very minimal Steve Jobs inspired styling inside a single file
TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ApplyBot Setup</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f7;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            color: #1d1d1f;
        }
        .container {
            background-color: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.04);
            width: 100%;
            max-width: 500px;
        }
        h1 {
            font-weight: 600;
            font-size: 28px;
            margin-bottom: 8px;
            text-align: center;
        }
        p.subtitle {
            text-align: center;
            color: #86868b;
            margin-bottom: 30px;
            font-size: 15px;
        }
        .step {
            display: none;
        }
        .step.active {
            display: block;
            animation: fadeIn 0.4s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        label {
            display: block;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 8px;
            color: #1d1d1f;
        }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 12px 16px;
            margin-bottom: 20px;
            border: 1px solid #d2d2d7;
            border-radius: 12px;
            box-sizing: border-box;
            font-size: 15px;
            font-family: 'Inter', sans-serif;
            background: rgba(255, 255, 255, 0.9);
            transition: all 0.3s;
        }
        input:focus {
            outline: none;
            border-color: #0071e3;
            box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.1);
        }
        button {
            width: 100%;
            padding: 14px;
            background-color: #0071e3;
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.3s, transform 0.1s;
        }
        button:hover {
            background-color: #0077ed;
        }
        button:active {
            transform: scale(0.98);
        }
        .btn-secondary {
            background-color: #e8e8ed;
            color: #1d1d1f;
            margin-top: 10px;
        }
        .btn-secondary:hover {
            background-color: #d2d2d7;
        }
        #success-message {
            text-align: center;
        }
        .success-icon {
            font-size: 48px;
            color: #34c759;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>ApplyBot Setup</h1>
        <p class="subtitle">Let's get everything ready for you.</p>

        <form id="setupForm">
            <!-- Step 1: Account -->
            <div id="step-1" class="step active">
                <label for="li_username">LinkedIn Email / Username</label>
                <input type="text" id="li_username" name="li_username" placeholder="you@example.com">
                
                <label for="li_password">LinkedIn Password</label>
                <input type="password" id="li_password" name="li_password" placeholder="••••••••">

                <label for="gemini_key">Gemini API Key</label>
                <input type="password" id="gemini_key" name="gemini_key" placeholder="AIzaSy...">

                <button type="button" onclick="nextStep(2)">Continue</button>
            </div>

            <!-- Step 2: Job Hunt Preferences -->
            <div id="step-2" class="step">
                <label for="search_terms">Target Roles (comma separated)</label>
                <input type="text" id="search_terms" name="search_terms" placeholder="e.g. Software Engineer, React Developer">
                
                <label for="search_location">Target Location</label>
                <input type="text" id="search_location" name="search_location" placeholder="e.g. San Francisco, California">

                <button type="button" onclick="nextStep(3)">Continue</button>
                <button type="button" class="btn-secondary" onclick="nextStep(1)">Back</button>
            </div>

            <!-- Step 3: Resume -->
            <div id="step-3" class="step">
                <label for="resume_path">Absolute Path to Resume PDF</label>
                <input type="text" id="resume_path" name="resume_path" placeholder="/Users/name/Documents/resume.pdf">

                <button type="button" onclick="submitForm()">Complete Setup</button>
                <button type="button" class="btn-secondary" onclick="nextStep(2)">Back</button>
            </div>

            <!-- Success -->
            <div id="step-success" class="step">
                <div id="success-message">
                    <div class="success-icon">✓</div>
                    <h2>You're all set.</h2>
                    <p>You can now run <br><code>python -m applybot</code><br>in your terminal.</p>
                </div>
            </div>
        </form>
    </div>

    <script>
        function nextStep(step) {
            document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
            document.getElementById(`step-${step}`).classList.add('active');
        }

        async function submitForm() {
            const formData = {
                li_username: document.getElementById('li_username').value,
                li_password: document.getElementById('li_password').value,
                gemini_key: document.getElementById('gemini_key').value,
                search_terms: document.getElementById('search_terms').value,
                search_location: document.getElementById('search_location').value,
                resume_path: document.getElementById('resume_path').value,
            };

            // Switch to loading/success view
            nextStep('success');

            await fetch('/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
        }
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(TEMPLATE)

@app.route("/submit", methods=["POST"])
def submit():
    data = request.json

    # Parse preferences for user.settings.json
    search_terms = [t.strip() for t in data.get("search_terms", "").split(",") if t.strip()]
    if not search_terms:
        search_terms = ["Software Engineer"] # Default
        
    user_settings = {
        "search_terms": search_terms,
        "search_location": data.get("search_location", ""),
        "default_resume_path": data.get("resume_path", "")
    }

    os.makedirs("config", exist_ok=True)
    with open(os.path.join("config", "user.settings.json"), "w", encoding="utf-8") as f:
        json.dump(user_settings, f, indent=4)
        
    # Safely generate secrets.py from jinja-like template string
    secrets_content = f'''# config/secrets.py (Auto-generated by Setup)
username = "{data.get("li_username", "")}"
password = "{data.get("li_password", "")}"

use_AI = True
ai_provider = "gemini"

GEMINI_API_KEY = "{data.get("gemini_key", "")}"
GEMINI_MODEL = "gemini-2.0-flash-lite"

# Legacy / Global settings (kept for backward compatibility)
llm_api_key = GEMINI_API_KEY
llm_api_url = "https://generativelanguage.googleapis.com/v1beta"
llm_model = GEMINI_MODEL
llm_spec = "gemini"

stream_output = False
showAiErrorAlerts = True
'''
    with open(os.path.join("config", "secrets.py"), "w", encoding="utf-8") as f:
        f.write(secrets_content)
        
    # Write success marker
    with open(os.path.join("config", ".setup_complete"), "w", encoding="utf-8") as f:
        f.write("version: 1")

    return jsonify({"status": "success"})


def main():
    print("Welcome to ApplyBot Setup UI.")
    print("Please open http://127.0.0.1:5000/ in your browser to configure the bot seamlessly.")
    app.run(host="127.0.0.1", port=5000, debug=False)

if __name__ == "__main__":
    main()
