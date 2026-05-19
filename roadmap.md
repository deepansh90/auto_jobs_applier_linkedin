# Roadmap

## 🚀 Recently Completed
- **Modular Package Layout**: Refactored the entire project into the `applybot/` package with clean separation of concerns (`browser`, `ui`, `ai`, `resumes`).
- **Setup Wizard (Flask UI)**: Local web interface for easy configuration of LinkedIn credentials, resume parsing, and search preferences.
- **Unified AI Provider Support**: Integrated Gemini and OpenAI/Local LLM support with a consistent interface and robust error handling.
- **Resilient Form Navigation**: Implemented stale-element recovery and multi-step retries for "Next", "Review", and "Submit" buttons.
- **Structural UI Locators**: Switched to CSS/XPath-based locators (e.g., `artdeco-button--primary`) to withstand LinkedIn's A/B testing and localized labels.
- **Centralized Config Overlay**: Improved configuration management via `user.settings.json` to avoid fragile regex-based file modifications.
- **Automated CI Regression**: Established a robust test suite (pytest) that runs in GitHub Actions with mock configuration support.
- **Hardened Limits & Safety Controls**: Implemented a dynamic daily application limit of 7 jobs (tracked via history CSV), real-time anti-bot/CAPTCHA emergency stop, automatic 7-day log self-cleanup, and resolved years of experience extraction NameError bugs.

## 🎯 Next Steps (Short Term)
- **#1 Enhanced Question Memory**: Store "Learned Answers" with better categorization to avoid re-asking the same dynamic questions across different jobs.
- **#2 Smart Skill Extraction**: Improve the resume parser to identify years of experience for specific technologies more accurately during onboarding.
- **#3 Desktop Notifications**: Add optional system alerts (macOS/Windows/Linux) for events like successful applications or required manual intervention (CAPTCHAs).

## 🔭 Future Vision (Long Term)
- **#4 Multi-Account Management**: Support switching between different LinkedIn profiles and resume sets seamlessly.
- **#5 Headless Mode Stability**: Further harden pop-up and modal handling to ensure 100% reliable headless execution.
- **#6 PDF Personalization**: Experiment with dynamic resume generation/modifications based on job descriptions (AI-driven tailoring).
- **#7 Advanced Analytics Dashboard**: A simple local dashboard to visualize application success rates, skipped reasons, and job matching scores over time.

## 🛠️ Performance & Hygiene
- **#8 Speed Wins**: Continue replacing fixed delays with `WebDriverWait` signals.
- **#9 Narrow Exception Catching**: Transition from `except Exception` to specific Selenium/AI error types for cleaner debugging.
- **#10 Refined Stale-Element Logic**: Further reduce retry overhead for even faster form submissions.
