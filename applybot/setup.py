import os
import json
import argparse
import secrets
import threading
import time
import webbrowser
import requests
from flask import Flask, render_template_string, request, jsonify

from applybot.resume_autofill import ensure_profile
from applybot.onboarding.profile_form import generate_all_configs

app = Flask(__name__)

TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ApplyBot | Setup Wizard</title>
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
            font-family: -apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            background-color: var(--li-bg);
            color: var(--li-text);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
            box-sizing: border-box;
        }
        .card {
            background-color: var(--li-white);
            border-radius: 8px;
            box-shadow: 0 0 0 1px rgba(0,0,0,0.08), 0 4px 4px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 600px;
            padding: 32px;
            transition: all 0.3s ease;
        }
        .header { text-align: center; margin-bottom: 24px; }
        .logo { font-size: 24px; font-weight: 700; color: var(--li-blue); display: flex; align-items: center; justify-content: center; gap: 4px; }
        .logo span { background: var(--li-blue); color: white; padding: 0 4px; border-radius: 2px; }
        h1 { font-size: 24px; font-weight: 400; margin: 8px 0; }
        p.subtitle { color: var(--li-secondary-text); font-size: 14px; margin-top: 0; }
        .step { display: none; }
        .step.active { display: block; animation: slideIn 0.3s ease-out; }
        @keyframes slideIn { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }
        
        .form-group { margin-bottom: 20px; text-align: left; }
        .form-row { display: flex; gap: 12px; margin-bottom: 20px; }
        .form-row > div { flex: 1; }
        label { display: block; font-size: 14px; font-weight: 600; margin-bottom: 4px; }
        input, select, textarea { width: 100%; padding: 10px 12px; border: 1px solid rgba(0,0,0,0.6); border-radius: 4px; font-size: 14px; box-sizing: border-box; font-family: inherit; }
        input:focus, select:focus, textarea:focus { outline: none; border: 2px solid var(--li-blue); padding: 9px 11px; }
        .btn { background-color: var(--li-blue); color: white; border: none; border-radius: 24px; padding: 12px 24px; font-size: 16px; font-weight: 600; cursor: pointer; width: 100%; margin-top: 16px; }
        .btn:hover { background-color: var(--li-blue-hover); }
        .btn-secondary { background-color: transparent; color: var(--li-secondary-text); margin-top: 12px; font-size: 14px; text-decoration: underline; cursor: pointer; border: none; width: 100%; }
        .progress-bar { height: 4px; background: #ebebeb; border-radius: 2px; margin-bottom: 24px; overflow: hidden; }
        .progress-fill { height: 100%; background: var(--li-blue); transition: width 0.3s; }
        .spinner { display: none; border: 3px solid rgba(0,0,0,0.1); width: 24px; height: 24px; border-radius: 50%; border-left-color: var(--li-blue); animation: spin 1s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .highlight-warning { border-color: #F5C252; background-color: #FEF8EA; }
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <div class="logo">Apply<span>Bot</span></div>
            <h1 id="title">Welcome</h1>
            <p class="subtitle" id="subtitle">Configure your automation profile.</p>
        </div>
        <div class="progress-bar"><div class="progress-fill" id="progress" style="width: 20%;"></div></div>

        <form id="setupForm">
            <!-- Step 1: Account -->
            <div id="step-1" class="step active">
                <div class="form-group">
                    <label>LinkedIn Email</label>
                    <input type="text" id="li_username" placeholder="you@example.com" required>
                </div>
                <div class="form-group">
                    <label>LinkedIn Password</label>
                    <input type="password" id="li_password" placeholder="Password" required>
                </div>
                <div class="form-group">
                    <label>AI Provider</label>
                    <select id="ai_provider">
                        <option value="gemini" id="opt-gemini">Gemini (Cloud)</option>
                        <option value="openai" id="opt-openai">Local LLM / OpenAI Compatible</option>
                    </select>
                </div>
                <div class="form-group" id="api_key_group">
                    <label>API Key</label>
                    <input type="password" id="api_key" placeholder="AIza... or Leave empty for local">
                </div>
                <button type="button" class="btn" onclick="nextStep(2)">Next: Resume</button>
            </div>

            <!-- Step 2: Resume Upload -->
            <div id="step-2" class="step">
                <div class="form-group">
                    <label>Path to your PDF Resume</label>
                    <input type="text" id="resume_path" placeholder="/Users/name/resume.pdf" required>
                    <p style="font-size: 12px; color: var(--li-secondary-text);">We will scan this resume now to auto-fill the rest of your configuration.</p>
                </div>
                <div id="resume-spinner" class="spinner"></div>
                <p id="resume-status" style="text-align:center; font-size: 12px; color: var(--li-secondary-text); display:none;">Extracting facts using AI...</p>
                <button type="button" class="btn" onclick="parseResume()" id="btn-parse-resume">Analyze Resume</button>
                <button type="button" class="btn-secondary" onclick="nextStep(1)">Back</button>
            </div>

            <!-- Step 3: Extracted Facts -->
            <div id="step-3" class="step">
                <p style="font-size: 13px; margin-bottom: 15px;">We extracted these details. Please correct any mistakes or fill missing fields.</p>
                <div class="form-row">
                    <div>
                        <label>First Name</label>
                        <input type="text" id="first_name">
                    </div>
                    <div>
                        <label>Last Name</label>
                        <input type="text" id="last_name">
                    </div>
                </div>
                <div class="form-row">
                    <div>
                        <label>Phone</label>
                        <input type="text" id="phone_number">
                    </div>
                    <div>
                        <label>Location (City, State, Country)</label>
                        <input type="text" id="location">
                    </div>
                </div>
                <div class="form-group">
                    <label>Current Employer</label>
                    <input type="text" id="recent_employer">
                </div>
                <div class="form-group">
                    <label>Headline</label>
                    <input type="text" id="headline">
                </div>
                <div class="form-group">
                    <label>Total Years of Experience</label>
                    <input type="number" id="years_of_experience">
                </div>
                <button type="button" class="btn" onclick="nextStep(4)">Next: Job Preferences</button>
                <button type="button" class="btn-secondary" onclick="nextStep(2)">Back</button>
            </div>

            <!-- Step 4: Job Preferences -->
            <div id="step-4" class="step">
                <div class="form-group">
                    <label>Job Title Keywords (comma separated)</label>
                    <input type="text" id="search_terms" placeholder="Software Engineer, Data Scientist">
                </div>
                <div class="form-group">
                    <label>Expected Salary (Annual)</label>
                    <input type="number" id="desired_salary" placeholder="100000">
                </div>
                <div class="form-group">
                    <label>Job Location Filters (LinkedIn Search)</label>
                    <input type="text" id="search_location" placeholder="New York, United States">
                </div>
                <button type="button" class="btn" onclick="nextStep(5)">Next: Compliance & Skills</button>
                <button type="button" class="btn-secondary" onclick="nextStep(3)">Back</button>
            </div>

            <!-- Step 5: Compliance & Skills -->
            <div id="step-5" class="step">
                <div class="form-row">
                    <div>
                        <label>Require Visa Sponsorship?</label>
                        <select id="require_visa">
                            <option value="No">No</option>
                            <option value="Yes">Yes</option>
                        </select>
                    </div>
                    <div>
                        <label>US Citizenship Status</label>
                        <select id="us_citizenship">
                            <option value="U.S. Citizen/Permanent Resident">U.S. Citizen/Permanent Resident</option>
                            <option value="Non-citizen allowed to work for any employer">Non-citizen allowed to work for any employer</option>
                            <option value="Non-citizen seeking work authorization">Non-citizen seeking work authorization</option>
                            <option value="Other">Other</option>
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div>
                        <label>Gender</label>
                        <select id="gender">
                            <option value="Decline">Decline</option>
                            <option value="Male">Male</option>
                            <option value="Female">Female</option>
                            <option value="Other">Other</option>
                        </select>
                    </div>
                    <div>
                        <label>Veteran Status</label>
                        <select id="veteran_status">
                            <option value="Decline">Decline</option>
                            <option value="No">No</option>
                            <option value="Yes">Yes</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label>Top Skills Matrix (Years of Experience)</label>
                    <p style="font-size: 11px; color: var(--li-secondary-text); margin-top: 0;">Fill these out to auto-answer dropdowns for required skills.</p>
                    <div id="skills_container" style="background: #f8f8f8; padding: 12px; border-radius: 4px; max-height: 150px; overflow-y: auto;">
                        <p style="font-size:12px; color:gray; text-align:center;">Extracting resume first...</p>
                    </div>
                </div>
                <button type="button" class="btn" onclick="submitForm()">Generate Configs & Finish</button>
                <button type="button" class="btn-secondary" onclick="nextStep(4)">Back</button>
            </div>

            <!-- Success -->
            <div id="step-success" class="step" style="text-align:center;">
                <h2 style="color: var(--li-blue);">All Configurations Generated!</h2>
                <p>Personals, Questions, Answers, and Custom Rules have been built.</p>
                <div style="padding: 20px; font-family: monospace; background: #f8f8f8; border-radius: 4px; font-size: 13px; margin-bottom: 20px; line-height: 1.6;">
                    python -m applybot --doctor
                </div>
                <button type="button" class="btn" onclick="runDoctor()">Validate Config Now</button>
                <p id="doctor_result" style="font-size: 12px; margin-top: 15px; text-align:left; white-space: pre-wrap; background: #eee; padding: 10px; border-radius: 4px; display: none;"></p>
            </div>
        </form>
    </div>

    <script>
        let extractedSkills = [];

        function nextStep(step) {
            document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
            document.getElementById(`step-${step}`).classList.add('active');
            document.getElementById('progress').style.width = (step / 5 * 100) + '%';
            
            const titles = {
                1: "Account Settings",
                2: "Resume Sync",
                3: "Verify Facts",
                4: "Job Search Preferences",
                5: "Compliance & Skills"
            };
            document.getElementById('title').innerText = titles[step] || "Setup";
        }

        async function parseResume() {
            const resumePath = document.getElementById('resume_path').value;
            const aiProvider = document.getElementById('ai_provider').value;
            const apiKey = document.getElementById('api_key').value;

            if (!resumePath) {
                alert("Please enter your resume path");
                return;
            }

            document.getElementById('resume-spinner').style.display = 'block';
            document.getElementById('resume-status').style.display = 'block';
            document.getElementById('btn-parse-resume').disabled = true;

            try {
                const resp = await fetch('/parse_resume', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ resume_path: resumePath, ai_provider: aiProvider, api_key: apiKey })
                });
                
                const data = await resp.json();
                if (data.status === 'success') {
                    // Populate step 3
                    const p = data.profile;
                    document.getElementById('first_name').value = p.name ? p.name.split(' ')[0] : '';
                    document.getElementById('last_name').value = p.name ? p.name.split(' ').slice(1).join(' ') : '';
                    document.getElementById('phone_number').value = p.phone || '';
                    document.getElementById('location').value = p.location || '';
                    document.getElementById('recent_employer').value = p.recent_employer || '';
                    document.getElementById('headline').value = p.title || '';
                    document.getElementById('years_of_experience').value = p.total_experience_years || '0';
                    
                    // Highlight missing
                    ['first_name', 'last_name', 'phone_number'].forEach(id => {
                        if (!document.getElementById(id).value) document.getElementById(id).classList.add('highlight-warning');
                    });

                    // Pre-fill Step 4 search terms guess
                    if (p.title) {
                        document.getElementById('search_terms').value = p.title;
                    }

                    // Populate Step 5 Skills
                    const sc = document.getElementById('skills_container');
                    sc.innerHTML = '';
                    extractedSkills = p.skills || [];
                    if (extractedSkills.length === 0) {
                        sc.innerHTML = '<p style="font-size:12px; color:gray;">No skills detected. Add them manually later.</p>';
                    } else {
                        extractedSkills.forEach((skill, i) => {
                            sc.innerHTML += `
                                <div style="display:flex; justify-content:space-between; margin-bottom:8px; align-items:center;">
                                    <span style="font-size:13px; font-weight:500;">${skill}</span>
                                    <input type="number" id="skill_${i}" placeholder="Yrs" style="width: 80px; padding: 4px 8px;">
                                </div>
                            `;
                        });
                    }

                    nextStep(3);
                } else {
                    alert("Error extracting resume: " + data.error);
                }
            } catch(e) {
                alert("Network error: " + e);
            }

            document.getElementById('resume-spinner').style.display = 'none';
            document.getElementById('resume-status').style.display = 'none';
            document.getElementById('btn-parse-resume').disabled = false;
        }

        async function submitForm() {
            const formData = {
                li_username: document.getElementById('li_username').value,
                li_password: document.getElementById('li_password').value,
                ai_provider: document.getElementById('ai_provider').value,
                api_key: document.getElementById('api_key').value,
                resume_path: document.getElementById('resume_path').value,
                first_name: document.getElementById('first_name').value,
                last_name: document.getElementById('last_name').value,
                phone_number: document.getElementById('phone_number').value,
                current_city: document.getElementById('location').value, // Used for 'current_city'
                location: document.getElementById('location').value,
                recent_employer: document.getElementById('recent_employer').value,
                headline: document.getElementById('headline').value,
                years_of_experience: document.getElementById('years_of_experience').value,
                search_terms: document.getElementById('search_terms').value,
                search_location: document.getElementById('search_location').value,
                desired_salary: document.getElementById('desired_salary').value,
                require_visa: document.getElementById('require_visa').value,
                us_citizenship: document.getElementById('us_citizenship').value,
                gender: document.getElementById('gender').value,
                veteran_status: document.getElementById('veteran_status').value,
                skills_matrix: {}
            };

            extractedSkills.forEach((skill, i) => {
                const yr = document.getElementById(`skill_${i}`).value;
                if (yr) formData.skills_matrix[skill] = yr;
            });

            const resp = await fetch('/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (resp.ok) {
                document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
                document.getElementById('step-success').classList.add('active');
                document.getElementById('progress').style.width = '100%';
                document.getElementById('title').innerText = "All Done!";
                document.getElementById('subtitle').innerText = "Configuration generated.";
            } else {
                const err = await resp.json();
                alert("Error: " + (err.error || "Failed to save configuration"));
            }
        }

        async function runDoctor() {
            const drBtn = event.target;
            drBtn.innerText = "Running Validation...";
            drBtn.disabled = true;

            const resp = await fetch('/doctor');
            const data = await resp.json();
            
            const resEl = document.getElementById('doctor_result');
            resEl.style.display = 'block';
            resEl.innerText = data.output;
            
            drBtn.innerText = "Validate Config Now";
            drBtn.disabled = false;
            
            if (data.status === 'success') {
                resEl.style.backgroundColor = '#E6F4EA';
            } else {
                resEl.style.backgroundColor = '#FCE8E6';
            }
        }

        // Auto-detect local LLM on load
        window.onload = async () => {
            const resp = await fetch('/detect_llm');
            const data = await resp.json();
            if (data.has_local) {
                document.getElementById('ai_provider').value = 'openai';
                document.getElementById('api_key').placeholder = "Detected Local LLM. Leave empty.";
            }
        };
    </script>
</body>
</html>
"""

def _inject_placeholder_examples(html: str) -> str:
    ph_email = f"you.{secrets.token_hex(3)}@example.invalid"
    ph_pass = f"Ex_{secrets.token_hex(4)}!0"
    ph_resume = f"/Users/you/Documents/resume_{secrets.token_hex(2)}.pdf"
    ph_gem = f"AIza{secrets.token_hex(12)}…"
    return html.replace("you@example.com", ph_email).replace("Password", ph_pass).replace("/Users/name/resume.pdf", ph_resume)

@app.route("/")
def home():
    return render_template_string(_inject_placeholder_examples(TEMPLATE))

@app.route("/detect_llm")
def detect_llm():
    # Simple check if local Ollama or LM Studio is running
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=1.0)
        if r.status_code == 200: return jsonify({"has_local": True})
    except: pass
    
    try:
        r = requests.get("http://localhost:1234/v1/models", timeout=1.0)
        if r.status_code == 200: return jsonify({"has_local": True})
    except: pass
    
    return jsonify({"has_local": False})

@app.route("/parse_resume", methods=["POST"])
def parse_resume():
    data = request.json
    config_dir = "config"
    os.makedirs(config_dir, exist_ok=True)
    
    # Temporarily write secrets so extraction works
    ai_prov = data.get("ai_provider", "gemini")
    key = data.get("api_key", "")
    with open(os.path.join(config_dir, "secrets.py"), "w", encoding="utf-8") as f:
        f.write(f'use_AI = True\nai_provider = "{ai_prov}"\n')
        if ai_prov == "gemini":
            f.write(f'GEMINI_API_KEY = "{key}"\nllm_api_key = "{key}"\n')
        else:
            f.write(f'OPENAI_API_KEY = "{key}"\nllm_api_key = "{key}"\n')

    resume_path = data.get("resume_path", "")
    if not resume_path or not os.path.exists(resume_path):
        return jsonify({"status": "error", "error": "Resume file not found at path."})
        
    try:
        profile = ensure_profile(config_dir, resume_path)
        return jsonify({"status": "success", "profile": profile})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route("/submit", methods=["POST"])
def submit():
    data = request.json
    config_dir = "config"
    os.makedirs(config_dir, exist_ok=True)

    # 1. Generate secrets.py
    ai_prov = data.get("ai_provider", "gemini")
    key = data.get("api_key", "")
    secrets_content = f'''# config/secrets.py (Auto-generated by Setup)
username = "{data.get('li_username', '')}"
password = "{data.get('li_password', '')}"
use_AI = True
ai_provider = "{ai_prov}"
'''
    if ai_prov == "gemini":
        secrets_content += f'GEMINI_API_KEY = "{key}"\nOPENAI_API_KEY = ""\nllm_api_key = "{key}"\n'
    else:
        secrets_content += f'OPENAI_API_KEY = "{key}"\nGEMINI_API_KEY = ""\nllm_api_key = "{key}"\n'
        
    with open(os.path.join(config_dir, "secrets.py"), "w", encoding="utf-8") as f:
        f.write(secrets_content)

    # 2. Generate user.settings.json
    search_terms = [t.strip() for t in data.get("search_terms", "").split(",") if t.strip()]
    user_settings = {
        "search_terms": search_terms if search_terms else ["Software Engineer"],
        "search_location": data.get("search_location", "Noida"),
        "default_resume_path": data.get("resume_path", ""),
        "desired_salary": int(data.get("desired_salary") or 0)
    }
    with open(os.path.join(config_dir, "user.settings.json"), "w", encoding="utf-8") as f:
        json.dump(user_settings, f, indent=4)
        
    # 3. Generate personals, questions, answers, custom_questions
    try:
        generate_all_configs(config_dir, data)
    except Exception as e:
        return jsonify({"status": "error", "error": f"Failed config generation: {e}"})

    with open(os.path.join(config_dir, ".setup_complete"), "w", encoding="utf-8") as f:
        f.write("version: 1")

    return jsonify({"status": "success"})

@app.route("/doctor")
def run_doctor():
    import subprocess
    try:
        result = subprocess.run(
            ["python", "-m", "applybot", "--doctor"], 
            capture_output=True, text=True, timeout=10
        )
        return jsonify({
            "status": "success" if result.returncode == 0 else "error", 
            "output": result.stdout + result.stderr
        })
    except Exception as e:
        return jsonify({"status": "error", "output": str(e)})

def main() -> None:
    parser = argparse.ArgumentParser(description="ApplyBot 5-step local web onboarding.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
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
            try: webbrowser.open(url)
            except Exception: pass
        threading.Thread(target=_open_when_ready, daemon=True).start()

    app.run(host=args.host, port=args.port, debug=False)

if __name__ == "__main__":
    main()
