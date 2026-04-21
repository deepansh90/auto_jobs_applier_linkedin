from __future__ import annotations

# Imports
import os
import sys
import csv
import re
import time

# Set CSV field size limit to prevent field size errors
csv.field_size_limit(1000000)  # Set to 1MB instead of default 131KB

from random import choice, shuffle, randint
from datetime import datetime
from urllib.parse import quote_plus, urlparse

from applybot.typeahead_helpers import pick_best_typeahead_index

LEARNING_MODE = False  # True = collect questions only (skips submit when pause-before-submit path runs). False = normal applies.

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, NoSuchWindowException, ElementNotInteractableException, WebDriverException, InvalidSessionIdException, StaleElementReferenceException

from applybot.config_loader import apply_user_overlay
apply_user_overlay()

from applybot.migrations import migrate_legacy_directories
migrate_legacy_directories()

from config.search import *
from config.secrets import use_AI, username, password, ai_provider, llm_api_key
from config.settings import *

# Allow CI / E2E harness to cap applies without editing committed settings.
_maj_env = (os.environ.get("MAX_APPLIED_JOBS") or "").strip()
if _maj_env.isdigit():
    import config.settings as _settings_cap

    _cap = max(1, int(_maj_env))
    _settings_cap.max_applied_jobs = _cap
    max_applied_jobs = _cap

# One-time resume -> profile.json autofill (new-user flow). No-op when profile.json exists.
try:
    from applybot.resume_autofill import ensure_profile as _ensure_profile
    _ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _CONFIG_DIR = os.path.join(_ROOT_DIR, "config")
    _RESUME_PATH = os.path.join(_ROOT_DIR, globals().get("default_resume_path", "") or "resume.pdf")
    _ensure_profile(_CONFIG_DIR, _RESUME_PATH)
except Exception as _autofill_err:
    print(f"[autofill] skipped: {_autofill_err}")

# Legacy personals/questions: real modules win; compat fills only what is missing (no `import *` overwrite).
try:
    from config.personals import *  # noqa: F401,F403
    _need_compat_personals = False
except ImportError:
    _need_compat_personals = True
try:
    from config.questions import *  # noqa: F401,F403
    _need_compat_questions = False
except ImportError:
    _need_compat_questions = True
if _need_compat_personals or _need_compat_questions:
    from config._compat import apply_compat_to_run_globals

    apply_compat_to_run_globals(globals(), _need_compat_personals, _need_compat_questions)

try:
    from config.custom_questions import custom_answers
except ImportError:
    custom_answers = {}

from applybot.browser import *
from applybot.helpers import *
from applybot.ui import *
from applybot.validator import validate_config


DEBUG_VERBOSE = os.environ.get("DEBUG_VERBOSE", "0") == "1"


def dbg(msg: str) -> None:
    """Gated debug logger. Off by default; set DEBUG_VERBOSE=1 to enable."""
    if DEBUG_VERBOSE:
        print_lg(f"[DEBUG] {msg}")


_DATE_POSTED_TPR = {
    "Any time": None,
    "Past month": "r2592000",
    "Past week": "r604800",
    "Past 24 hours": "r86400",
}

_JOB_TYPE_CODE = {
    "Full-time": "F", "Part-time": "P", "Contract": "C", "Temporary": "T",
    "Volunteer": "V", "Internship": "I", "Other": "O",
}

_WORKPLACE_CODE = {"On-site": "1", "Remote": "2", "Hybrid": "3"}

_EXP_LEVEL_CODE = {
    "Internship": "1", "Entry level": "2", "Associate": "3",
    "Mid-Senior level": "4", "Director": "5", "Executive": "6",
}


def build_linkedin_jobs_search_url(keywords: str) -> str:
    '''
    Builds the LinkedIn job search URL for a keyword. Embeds every supported filter
    directly as URL query params so we don't depend on LinkedIn's filter UI
    (which keeps changing between classic and pill-based layouts).

    URL params used:
      - f_WT: workplace types (1=On-site, 2=Remote, 3=Hybrid)
      - f_EA=true: Easy Apply (f_AL is Actively hiring, NOT Easy Apply)
      - sortBy: DD = Most recent, R = Most relevant
      - f_TPR: date posted (r2592000=Past month, r604800=Past week, r86400=Past 24h)
      - f_JT: job types (F/P/C/T/V/I/O)
      - f_E: experience level (1..6)
    '''
    query = quote_plus(keywords.strip())
    params = [f"keywords={query}"]

    wt_codes = [_WORKPLACE_CODE[w] for w in (on_site or []) if w in _WORKPLACE_CODE] \
        or ["1", "2", "3"]
    params.append("f_WT=" + quote_plus(",".join(wt_codes)))

    if easy_apply_only:
        params.append("f_EA=true")

    if sort_by == "Most recent":
        params.append("sortBy=DD")
    elif sort_by == "Most relevant":
        params.append("sortBy=R")

    tpr = _DATE_POSTED_TPR.get(date_posted)
    if tpr:
        params.append(f"f_TPR={tpr}")

    jt_codes = [_JOB_TYPE_CODE[j] for j in (job_type or []) if j in _JOB_TYPE_CODE]
    if jt_codes:
        params.append("f_JT=" + quote_plus(",".join(jt_codes)))

    el_codes = [_EXP_LEVEL_CODE[e] for e in (experience_level or []) if e in _EXP_LEVEL_CODE]
    if el_codes:
        params.append("f_E=" + quote_plus(",".join(el_codes)))

    return "https://www.linkedin.com/jobs/search/?" + "&".join(params)


def assert_easy_apply_url_contains_f_ea(url: str) -> None:
    '''
    Ensures the LinkedIn jobs URL requests Easy Apply when easy_apply_only is enabled.
    Logs a clear error if the contract is broken.
    '''
    if easy_apply_only and "f_EA=true" not in url:
        msg = f"Expected f_EA=true in job search URL when easy_apply_only=True, got: {url}"
        print_lg(f"[ERROR] {msg}")
        raise RuntimeError(msg)

if use_AI:
    # --- AI PROVIDER IMPORTS ---
    # We import all available providers to allow for dynamic failover on quota limits.
    
    # OpenAI (Core)
    try:
        from applybot.ai.openaiConnections import (
            ai_create_openai_client, ai_extract_skills, ai_answer_question, 
            ai_close_openai_client, ai_check_job_relevance, ai_generate_resume
        )
        HAS_OPENAI = True
    except ImportError: HAS_OPENAI = False

    # Gemini
    try:
        from applybot.ai.geminiConnections import (
            gemini_create_client, gemini_extract_skills, gemini_answer_question,
            gemini_check_job_relevance, gemini_generate_resume
        )
        HAS_GEMINI = True
    except ImportError: HAS_GEMINI = False

    # --- FAILOVER DISPATCHER ---
    
    # Define provider priority: Preferred first, then others.
    all_providers = ["gemini", "openai"]
    preferred_provider = ai_provider if ai_provider in all_providers else "gemini"
    provider_priority = [preferred_provider] + [p for p in all_providers if p != preferred_provider]

    # Global client cache for failover
    __ai_clients = {}
    __disabled_providers: set[str] = set()

    try:
        from openai import AuthenticationError as _OpenAIAuthenticationError
        from openai import RateLimitError as _OpenAIRateLimitError
    except ImportError:
        _OpenAIRateLimitError = ()  # type: ignore[misc,assignment]
        _OpenAIAuthenticationError = ()  # type: ignore[misc,assignment]

    try:
        from google.api_core import exceptions as _google_api_core_exceptions
    except ImportError:
        _google_api_core_exceptions = None  # type: ignore[assignment]

    def _provider_has_valid_key(provider: str) -> bool:
        """Return True only if the provider has a real (non-placeholder) key configured."""
        if provider == "gemini":
            key = globals().get("GEMINI_API_KEY")
            return bool(key) and not str(key).startswith("YOUR_")
        if provider == "openai":
            key = globals().get("OPENAI_API_KEY")
            return bool(key) and key != "YOUR_OPENAI_API_KEY" and not str(key).startswith("YOUR_")
        return False

    def ai_call(method_name, *args, **kwargs):
        """
        Unified wrapper to call AI methods with automatic failover between providers.
        Supported methods: 'extract_skills', 'answer_question', 'check_relevance', 'generate_resume'
        """
        last_error = None
        for provider in provider_priority:
            if provider in __disabled_providers:
                continue
            if not _provider_has_valid_key(provider):
                # Disable once, quietly, to keep logs clean
                if provider not in __disabled_providers:
                    print_lg(f"Skipping {provider}: no valid API key configured.")
                    __disabled_providers.add(provider)
                continue
            try:
                # 1. Initialize client if not already cached
                client = __ai_clients.get(provider)
                if not client:
                    if provider == "gemini" and HAS_GEMINI:
                        client = gemini_create_client() 
                    elif provider == "openai" and HAS_OPENAI:
                        key = OPENAI_API_KEY
                        url = OPENAI_API_URL if 'OPENAI_API_URL' in globals() else None
                        model = OPENAI_MODEL if 'OPENAI_MODEL' in globals() else None
                        client = ai_create_openai_client(api_key=key, base_url=url, model_name=model)
                    
                    if client:
                        __ai_clients[provider] = client
                    else:
                        __disabled_providers.add(provider)
                        continue # Skip to next provider if client creation fails

                # 2. Map method to provider-specific function
                if provider == "gemini":
                    func_map = {
                        'extract_skills': gemini_extract_skills,
                        'answer_question': gemini_answer_question,
                        'check_relevance': gemini_check_job_relevance,
                        'generate_resume': gemini_generate_resume
                    }
                elif provider == "openai":
                    func_map = {
                        'extract_skills': ai_extract_skills,
                        'answer_question': ai_answer_question,
                        'check_relevance': ai_check_job_relevance,
                        'generate_resume': ai_generate_resume
                    }
                
                func = func_map.get(method_name)
                if not func: continue

                # 3. Call the function (passing the provider-specific client)
                # We replace the first arg (aiClient) if it exists, or just pass the current client
                call_args = list(args)
                if call_args:
                    call_args[0] = client # Replace old aiClient with the provider-specific one
                else:
                    call_args = [client]

                result = func(*call_args, **kwargs)
                
                # 4. Check for quota/auth errors in response
                if isinstance(result, dict) and "error" in result:
                    err_msg = str(result["error"]).lower()
                    if any(code in err_msg for code in ["401", "authentication", "invalid api key", "invalid_request_error"]):
                        print_lg(f"Auth error for {provider}. Disabling provider for this run.")
                        __disabled_providers.add(provider)
                        __ai_clients.pop(provider, None)
                        last_error = result["error"]
                        continue
                    if any(code in err_msg for code in ["429", "quota", "limit", "exhausted"]):
                        print_lg(f"Quota reached for {provider}. Attempting failover to next provider...")
                        last_error = result["error"]
                        continue
                
                return result

            except Exception as e:
                if isinstance(e, InvalidSessionIdException):
                    raise
                if _OpenAIRateLimitError and isinstance(e, _OpenAIRateLimitError):
                    print_lg(f"Quota error for {provider}: {e}. Switching provider...")
                    last_error = e
                    continue
                if _OpenAIAuthenticationError and isinstance(e, _OpenAIAuthenticationError):
                    print_lg(f"Auth error for {provider}: {e}. Disabling provider for this run.")
                    __disabled_providers.add(provider)
                    __ai_clients.pop(provider, None)
                    last_error = e
                    continue
                if _google_api_core_exceptions is not None and isinstance(
                    e, _google_api_core_exceptions.ResourceExhausted
                ):
                    print_lg(f"Quota error for {provider}: {e}. Switching provider...")
                    last_error = e
                    continue
                err_str = str(e).lower()
                if any(kw in err_str for kw in ["401", "authentication", "invalid api key", "api key"]):
                    print_lg(f"Auth error for {provider}: {e}. Disabling provider for this run.")
                    __disabled_providers.add(provider)
                    __ai_clients.pop(provider, None)
                    last_error = e
                    continue
                if any(kw in err_str for kw in ["429", "quota", "limit", "exhausted"]):
                    print_lg(f"Quota error for {provider}: {e}. Switching provider...")
                    last_error = e
                    continue
                raise e # Re-raise non-quota/unexpected errors
        
        # All providers exhausted/disabled -> enter offline mode
        if not globals().get("_OFFLINE_MODE_ANNOUNCED"):
            print_lg("All AI providers unavailable. Running in OFFLINE mode (skipping AI-dependent features).")
            globals()["_OFFLINE_MODE_ANNOUNCED"] = True
        else:
            print_lg(f"[OFFLINE] Skipping AI call '{method_name}' - no providers available.")
        return {"error": "offline_mode", "result": None, "last_error": str(last_error) if last_error else None}

    from applybot.resumes.resume_gen import generate_tailored_files
    import json

    def ai_text_answer(method_name: str, *args, **kwargs) -> str:
        '''
        Wrapper around ai_call that ALWAYS returns a plain string for text/textarea
        questions. When AI is offline (or returns an error dict), returns "" so
        the calling code can fall back to config values without crashing on
        ``text.send_keys({...})``.
        '''
        try:
            result = ai_call(method_name, *args, **kwargs)
        except Exception as e:
            print_lg(f"[AI] {method_name} raised: {e}")
            return ""
        if isinstance(result, dict):
            return ""
        if isinstance(result, str):
            return result
        return ""
else:
    def ai_text_answer(method_name: str, *args, **kwargs) -> str:
        return ""

from typing import Literal



# pyautogui.FAILSAFE = False
# if use_resume_generator:    from resume_generator import is_logged_in_GPT, login_GPT, open_resume_chat, create_custom_resume


#< Global Variables and logics

if run_in_background == True:
    pause_at_failed_question = False
    pause_before_submit = False
    run_non_stop = False

first_name = first_name.strip()
middle_name = middle_name.strip()
last_name = last_name.strip()
full_name = first_name + " " + middle_name + " " + last_name if middle_name else first_name + " " + last_name

useNewResume = True
randomly_answered_questions = set()

tabs_count = 1
easy_applied_count = 0
external_jobs_count = 0
failed_count = 0
skip_count = 0
dailyEasyApplyLimitReached = False

re_experience = re.compile(r'[(]?\s*(\d+)\s*[)]?\s*[-to]*\s*\d*[+]*\s*year[s]?', re.IGNORECASE)

desired_salary_lakhs = str(round(desired_salary / 100000, 2))
desired_salary_monthly = str(round(desired_salary/12, 2))
desired_salary = str(desired_salary)

current_ctc_lakhs = str(round(current_ctc / 100000, 2))
current_ctc_monthly = str(round(current_ctc/12, 2))
current_ctc = str(current_ctc)

notice_period_months = str(notice_period//30)
notice_period_weeks = str(notice_period//7)
notice_period = str(notice_period)

aiClient = None
##> ------ Dheeraj Deshwal : dheeraj9811 Email:dheeraj20194@iiitd.ac.in/dheerajdeshwal9811@gmail.com - Feature ------
about_company_for_ai = None # TODO extract about company for AI
##<

# Load Master Resume Data (legacy master_resume.json if present, else synthesize from profile.json)
master_resume_path = os.path.join("config", "master_resume.json")
master_resume_data = {}
if os.path.exists(master_resume_path):
    with open(master_resume_path, 'r') as f:
        master_resume_data = json.load(f)
        print_lg("---- MASTER RESUME LOADED SUCCESSFULLY ----")
else:
    try:
        from config._compat import synthesize_master_resume
        master_resume_data = synthesize_master_resume()
        if master_resume_data:
            print_lg("---- MASTER RESUME SYNTHESIZED FROM profile.json ----")
    except Exception as _syn_err:
        print_lg(f"[master_resume] synthesis skipped: {_syn_err}")

#>


#< Login Functions
def _linkedin_post_login_url(url: str, drv: WebDriver | None = None) -> bool:
    '''
    True when the browser has left the login wall and reached a normal signed-in surface.
    LinkedIn often lands on /jobs or /feed; waiting for /feed alone caused false timeouts.

    RCA: https://www.linkedin.com/jobs/ is the *public* jobs landing (login hero) and shares
    the /jobs host with real search URLs. Treat bare ``/jobs`` as signed-in only when the
    global nav is present (``drv`` required); otherwise require ``/jobs/search``, ``/jobs/view``, etc.
    '''
    low = (url or "").lower()
    if "linkedin.com/login" in low or "linkedin.com/uas/login" in low:
        return False
    if "linkedin.com/checkpoint/lg/login-submit" in low:
        return False
    if "linkedin.com/feed" in low or "linkedin.com/mynetwork" in low:
        return True
    if "linkedin.com/jobs" in low:
        try:
            path = (urlparse(url).path or "").rstrip("/")
        except Exception:
            path = "/jobs"
        if path == "/jobs":
            if drv is not None and try_find_by_classes(drv, ["global-nav", "nav-container"]):
                return True
            return False
        return True
    try:
        path = urlparse(url).path or ""
        if path.startswith("/in/") and "/login" not in low:
            return True
    except Exception:
        pass
    return False


def is_logged_in_LN() -> bool:
    '''
    Function to check if user is logged-in in LinkedIn
    * Returns: `True` if user is logged-in or `False` if not
    '''
    # Check if we are on the feed, jobs, or if the global navigation (nav-bar) is present
    if _linkedin_post_login_url(driver.current_url, driver):
        return True
    if "linkedin.com/checkpoint/lg/login-submit" in driver.current_url: return False
    
    # Check for nav bar
    nav = try_find_by_classes(driver, ["global-nav", "nav-container"])
    if nav: return True
    
    if try_linkText(driver, "Sign in"): return False
    if try_xp(driver, '//button[@type="submit" and contains(text(), "Sign in")]', click=False):
        return False
    if try_linkText(driver, "Join now"): return False
    
    # Final check: if we see the search bar, we're likely logged in
    search_bar = try_xp(driver, "//input[contains(@class, 'search-global-typeahead__input')]", click=False)
    if search_bar: return True
    
    print_lg("Didn't find Sign in link or Nav bar, assuming login state based on URL...")
    return _linkedin_post_login_url(driver.current_url, driver)


def _linkedin_input_typ(inp: WebElement) -> str:
    return (inp.get_attribute("type") or "text").lower()


def _linkedin_is_login_identifier_candidate(inp: WebElement) -> bool:
    """Skip global nav search, hidden controls, etc."""
    try:
        if not inp.is_displayed() or not inp.is_enabled():
            return False
    except Exception:
        return False
    typ = _linkedin_input_typ(inp)
    if typ in ("hidden", "submit", "button", "checkbox", "radio", "image", "file", "search"):
        return False
    if typ not in ("text", "email", "tel"):
        return False
    blob = " ".join(
        [
            (inp.get_attribute("name") or ""),
            (inp.get_attribute("id") or ""),
            (inp.get_attribute("class") or ""),
            (inp.get_attribute("aria-label") or ""),
            (inp.get_attribute("placeholder") or ""),
        ]
    ).lower()
    if any(x in blob for x in ("search", "typeahead", "jobs-search", "global-nav")):
        return False
    return True


def _linkedin_resolve_identifier_and_password_fields(drv: WebDriver) -> tuple[WebElement | None, WebElement | None]:
    """
    Pair the email/phone field with the password field.

    1) Prefer inputs inside the same <form> (classic LinkedIn).
    2) Fallback: document-order scan — the current /login UI is often a card with no <form>
       or nested markup where form-scoped queries return nothing.
    """
    for form in drv.find_elements(By.TAG_NAME, "form"):
        inputs = form.find_elements(By.CSS_SELECTOR, "input")
        text_before_pw: list[WebElement] = []
        password_el: WebElement | None = None
        for inp in inputs:
            try:
                if not inp.is_displayed() or not inp.is_enabled():
                    continue
            except Exception:
                continue
            typ = _linkedin_input_typ(inp)
            if typ == "password":
                password_el = inp
                break
            if typ in ("text", "email", "tel"):
                text_before_pw.append(inp)
        if password_el is None:
            continue
        identifier_el = text_before_pw[0] if text_before_pw else None
        if identifier_el is None:
            for inp in inputs:
                try:
                    if inp == password_el or not inp.is_displayed() or not inp.is_enabled():
                        continue
                except Exception:
                    continue
                typ = _linkedin_input_typ(inp)
                if typ in ("text", "email", "tel"):
                    identifier_el = inp
                    break
        if identifier_el and password_el:
            return identifier_el, password_el

    # No usable <form>: build a list of login-relevant inputs in DOM order (handles flex vs DOM order).
    ordered: list[tuple[WebElement, str]] = []
    for inp in drv.find_elements(By.CSS_SELECTOR, "input"):
        typ = _linkedin_input_typ(inp)
        if typ == "password":
            try:
                if inp.is_displayed() and inp.is_enabled():
                    ordered.append((inp, "pw"))
            except Exception:
                continue
            continue
        if _linkedin_is_login_identifier_candidate(inp):
            ordered.append((inp, "id"))

    for idx, (pw_el, kind) in enumerate(ordered):
        if kind != "pw":
            continue
        for j in range(idx - 1, -1, -1):
            if ordered[j][1] == "id":
                return ordered[j][0], pw_el
        for j in range(idx + 1, len(ordered)):
            if ordered[j][1] == "id":
                return ordered[j][0], pw_el

    # XPath hints (localized labels / autocomplete).
    try:
        pw = drv.find_elements(By.CSS_SELECTOR, "input[type='password']")
        for p in pw:
            try:
                if p.is_displayed() and p.is_enabled():
                    for xp in (
                        "//input[@autocomplete='username']",
                        "//input[contains(@name,'session')]",
                        "//input[contains(@aria-label,'mail') or contains(@aria-label,'hone')]",
                        "//input[contains(@placeholder,'mail') or contains(@placeholder,'hone')]",
                    ):
                        for cand in drv.find_elements(By.XPATH, xp):
                            if _linkedin_is_login_identifier_candidate(cand):
                                return cand, p
                    break
            except Exception:
                continue
    except Exception:
        pass

    return None, None


def _linkedin_login_identifier_visible(drv: WebDriver) -> bool:
    """True when we can resolve a visible identifier field + password (same test as fill)."""
    ident, pw = _linkedin_resolve_identifier_and_password_fields(drv)
    return bool(ident and pw)


def _linkedin_open_full_email_password_form() -> None:
    '''
    Persistent profiles often land on "Welcome back" with a remembered account card
    and no email field. Click through to the standard identifier + password form so
    secrets.py credentials can be filled reliably.
    '''
    sleep(0.6)
    for fragment in (
        "Sign in using another account",
        "Sign in with another account",
        "Use another account",
        "another account",  # partial match last — broadest
    ):
        try:
            for el in driver.find_elements(By.PARTIAL_LINK_TEXT, fragment):
                if not el.is_displayed():
                    continue
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                sleep(0.2)
                el.click()
                print_lg(f'Clicked "{fragment.strip()}" to leave remembered-account / Welcome back screen.')
                sleep(2.5)
                return
        except Exception:
            continue


def _linkedin_click_sign_submit_button(drv: WebDriver) -> bool:
    """
    LinkedIn's primary submit is often not `element_to_be_clickable` (overlays, animation,
    or text inside nested spans). Try many locators, then JS click, then form submit / Enter.
    """
    locators = [
        (By.CSS_SELECTOR, "button[data-id='sign-in-form__submit-btn']"),
        (By.XPATH, "//button[.//span[normalize-space(.)='Sign in']]"),
        (By.XPATH, "//button[.//span[contains(normalize-space(.),'Sign in')]]"),
        (By.XPATH, "//button[contains(normalize-space(.),'Sign in')]"),
        (By.XPATH, "//button[@type='submit' and contains(.,'Sign')]"),
        (By.XPATH, "//input[@type='submit' and contains(@value,'Sign')]"),
        (By.XPATH, "//input[@type='submit' and contains(@value,'sign')]"),
        (By.XPATH, "//*[@role='button' and contains(normalize-space(.),'Sign in')]"),
        (By.XPATH, "//form[.//input[@type='password']]//button[@type='submit']"),
        (By.CSS_SELECTOR, "form button.btn__primary--large[type='submit']"),
        (By.CSS_SELECTOR, "main button.btn__primary--large"),
    ]
    for by, sel in locators:
        try:
            for btn in drv.find_elements(by, sel):
                try:
                    if not btn.is_displayed():
                        continue
                except Exception:
                    continue
                try:
                    drv.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                except Exception:
                    pass
                sleep(0.25)
                try:
                    btn.click()
                except Exception:
                    try:
                        drv.execute_script("arguments[0].click();", btn)
                    except Exception:
                        continue
                print_lg(f"[login] clicked Sign in ({sel[:60]!r}…)")
                return True
        except Exception:
            continue

    try:
        ok = drv.execute_script(
            """
            const pw = document.querySelector("input[type='password']");
            if (!pw) return false;
            const r = pw.getBoundingClientRect();
            if (r.width < 1 || r.height < 1) return false;
            const form = pw.closest('form');
            if (form) {
              const btn = form.querySelector(
                "button[type='submit'], input[type='submit'], button.btn__primary--large"
              );
              if (btn && btn.getBoundingClientRect().width > 0) {
                btn.click();
                return true;
              }
              if (typeof form.requestSubmit === 'function') {
                try { form.requestSubmit(); return true; } catch (e) {}
              }
            }
            return false;
            """
        )
        if ok:
            print_lg("[login] clicked Sign in via JS (form submit / submit button near password)")
            return True
    except Exception:
        pass

    try:
        for pw in drv.find_elements(By.CSS_SELECTOR, "input[type='password']"):
            try:
                if pw.is_displayed() and pw.is_enabled():
                    pw.send_keys(Keys.ENTER)
                    print_lg("[login] submitted login with Enter on password field")
                    return True
            except Exception:
                continue
    except Exception:
        pass

    return False


def _linkedin_dismiss_blocking_layers(drv: WebDriver) -> None:
    """
    Public /jobs and /login often show a top strip (cookies, 'Agree & Join', etc.) that
    intercepts clicks so email/password never receive keystrokes.
    """
    selectors = [
        (By.PARTIAL_LINK_TEXT, "Agree & Join"),
        (By.PARTIAL_LINK_TEXT, "Continue to join"),
        (By.PARTIAL_LINK_TEXT, "Accept cookies"),
        (By.PARTIAL_LINK_TEXT, "Accept"),
        (By.XPATH, "//button[contains(.,'Accept')]"),
        (By.XPATH, "//button[contains(.,'Agree')]"),
        (By.CSS_SELECTOR, "[aria-label='Dismiss']"),
        (By.CSS_SELECTOR, "button.artdeco-global-alert__action"),
    ]
    for by, sel in selectors:
        try:
            for el in drv.find_elements(by, sel):
                try:
                    if not el.is_displayed() or not el.is_enabled():
                        continue
                except Exception:
                    continue
                try:
                    drv.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                except Exception:
                    pass
                sleep(0.12)
                try:
                    el.click()
                except Exception:
                    try:
                        drv.execute_script("arguments[0].click();", el)
                    except Exception:
                        continue
                print_lg(f"[login] dismissed blocking layer ({str(sel)[:48]}…)")
                sleep(0.5)
        except Exception:
            continue


def login_LN() -> None:
    '''
    Function to login for LinkedIn
    * Tries to login using given `username` and `password` from `secrets.py`
    * If failed, tries to login using saved LinkedIn profile button if available
    * If both failed, asks user to login manually
    '''
    # Find the username and password fields and fill them with user credentials.
    # Guest marketing page https://www.linkedin.com/jobs/ already shows the form — skip /login redirect.
    if not _linkedin_login_identifier_visible(driver):
        driver.get("https://www.linkedin.com/login")
    _linkedin_open_full_email_password_form()
    sleep(1.0)
    _linkedin_dismiss_blocking_layers(driver)
    if username == "username@example.com" and password == "example_password":
        smart_alert("User did not configure username and password in secrets.py, hence can't login automatically! Please login manually!", "Login Manually","Okay")
        print_lg("User did not configure username and password in secrets.py, hence can't login automatically! Please login manually!")
        manual_login_retry(is_logged_in_LN, 2)
        return
    try:
        # Wait for a driveable email/password path (legacy IDs, <form>, or card without <form>).
        WebDriverWait(driver, 40).until(_linkedin_login_identifier_visible)
        _linkedin_dismiss_blocking_layers(driver)
        select_all = Keys.COMMAND + "a" if sys.platform == "darwin" else Keys.CONTROL + "a"
        ident_el, pass_el = _linkedin_resolve_identifier_and_password_fields(driver)
        try:
            if ident_el and pass_el:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", ident_el)
                sleep(0.2)
                ident_el.click()
                ident_el.send_keys(select_all)
                ident_el.send_keys(username)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pass_el)
                sleep(0.2)
                pass_el.click()
                pass_el.send_keys(select_all)
                pass_el.send_keys(password)
            else:
                try:
                    text_input_by_ID(driver, "username", username, 2)
                except Exception:
                    try:
                        text_input_by_ID(driver, "session_key", username, 2)
                    except Exception:
                        sleep(1)
                        inputs = driver.find_elements(
                            By.XPATH,
                            '//input[@type="text" or @type="email"]',
                        )
                        for inp in inputs:
                            if inp.is_displayed() and inp.is_enabled():
                                inp.clear()
                                inp.send_keys(username)
                                break
                try:
                    text_input_by_ID(driver, "password", password, 2)
                except Exception:
                    try:
                        text_input_by_ID(driver, "session_password", password, 2)
                    except Exception:
                        sleep(1)
                        inputs = driver.find_elements(By.XPATH, "//input[@type='password']")
                        for inp in inputs:
                            if inp.is_displayed() and inp.is_enabled():
                                inp.clear()
                                inp.send_keys(password)
                                break
        except Exception:
            print_lg("Couldn't fill username/password (LinkedIn DOM may have changed again).")
        sleep(0.4)
        if not _linkedin_click_sign_submit_button(driver):
            print_lg("Could not find a clickable Sign in button; complete login manually if needed.")
    except Exception as e1:
        try:
            profile_button = find_by_class(driver, "profile__details")
            profile_button.click()
        except Exception:
            print_lg(
                "Login form did not appear as expected (LinkedIn UI change or already on a checkpoint). "
                "If credentials are in config/secrets.py, complete the browser window manually; the wait below still applies."
            )

    try:
        # Wait up to 3 minutes for successful redirect — long enough for OTP / 2FA / device verify.
        # We watch the URL rather than prompt so the user can finish the challenge in the open browser.
        print_lg(
            "Waiting for login to complete (OTP / CAPTCHA / device prompts: use the browser window; "
            "Google 'Continue as' cannot be filled by the bot—use email+password or finish manually). "
            "Up to 3 min..."
        )
        long_wait = WebDriverWait(driver, 180)
        long_wait.until(lambda d: _linkedin_post_login_url(d.current_url, d))
        return print_lg("Login successful!")
    except Exception:
        print_lg(
            "Login did not reach a logged-in URL within 3 min (OTP, CAPTCHA, wrong credentials, or LinkedIn UI change). "
            "Credentials come from config/secrets.py loaded at process start—restart runAiBot.py after editing secrets. "
            "Complete login in the browser if prompted."
        )
        # print_lg(e)
        manual_login_retry(is_logged_in_LN, 2)
#>



def get_applied_job_ids() -> set[str]:
    '''
    Function to get a `set` of applied job's Job IDs
    * Returns a set of Job IDs from existing applied jobs history csv file
    '''
    job_ids: set[str] = set()
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                job_ids.add(row[0])
    except FileNotFoundError:
        print_lg(f"The CSV file '{file_name}' does not exist.")
    return job_ids



def set_search_location() -> None:
    '''
    Function to set search location
    '''
    if search_location.strip():
        try:
            print_lg(f'Setting search location as: "{search_location.strip()}"')
            # Selectors for location box
            location_selectors = [
                ".//input[@aria-label='City, state, or zip code' and not(@disabled)]",
                ".//input[contains(@id, 'jobs-search-box-location-id')]",
                "//input[contains(@placeholder, 'Location')]"
            ]
            
            search_location_ele = None
            for selector in location_selectors:
                search_location_ele = try_xp(driver, selector, False)
                if search_location_ele: break
                
            if search_location_ele:
                # Clear existing text first
                search_location_ele.click()
                sleep(0.5)
                search_location_ele.send_keys(Keys.COMMAND, 'a')
                search_location_ele.send_keys(Keys.BACKSPACE)
                text_input(actions, search_location_ele, search_location, "Search Location")
            else:
                raise ElementNotInteractableException("Could not find search location input box")
        except (ElementNotInteractableException, Exception) as e:
            try:
                # Fallback: Tab through matching the keywords box
                try_xp(driver, ".//label[@class='jobs-search-box__input-icon jobs-search-box__keywords-label']")
                actions.send_keys(Keys.TAB, Keys.TAB).perform()
                # Clear existing
                actions.key_down(Keys.COMMAND).send_keys("a").key_up(Keys.COMMAND).send_keys(Keys.BACKSPACE).perform()
                actions.send_keys(search_location.strip()).perform()
                sleep(2)
                actions.send_keys(Keys.ENTER).perform()
            except:
                print_lg("Failed to update search location, continuing with default location!", e)
            try_xp(driver, ".//button[@aria-label='Cancel']")


def ensure_classic_search() -> None:
    '''
    Detects if LinkedIn is using the AI-powered search (Beta) and switches back to classic
    if necessary to ensure filter selectors remain valid.
    '''
    try:
        # Improved check for the AI-powered search dropdown button
        ai_beta_selectors = [
            "//button[.//span[text()='AI-powered search is in beta']]",
            "//button[contains(., 'AI-powered search is in beta')]",
            "//button[contains(., 'Try the new job search')]"
        ]
        
        ai_beta_btn = None
        for selector in ai_beta_selectors:
            ai_beta_btn = try_xp(driver, selector, False)
            if ai_beta_btn: break
            
        if ai_beta_btn:
            # OPTION 1: Try Force Classic via URL
            current_url = driver.current_url
            if "CLASSIC_SEARCH_MODE" not in current_url:
                print_lg("Detected AI-Beta layout. Attempting to force Classic mode via URL...")
                separator = "&" if "?" in current_url else "?"
                classic_url = current_url + separator + "origin=CLASSIC_SEARCH_MODE_FROM_SEMANTIC"
                driver.get(classic_url)
                sleep(5)
                # Check if we are still in beta
                if not try_xp(driver, "//button[.//span[text()='AI-powered search is in beta']]", False):
                    print_lg("Successfully forced classic mode via URL.")
                    return

            print_lg("URL force failed or already tried. Attempting UI-based switch...")
            # Click the dropdown button using JS for robustness
            try:
                driver.execute_script("arguments[0].click();", ai_beta_btn)
                sleep(2)
            except:
                pass
            
            # Precise switch back link based on subagent findings (Retrying multiple times)
            switch_selectors = [
                "//a[.//p[text()='Switch back to classic job search']]",
                "//span[contains(normalize-space(.), 'Switch back to classic')]/..",
                "//a[contains(@href, 'CLASSIC_SEARCH_MODE')]",
                "//*[contains(text(), 'Switch back to classic')]"
            ]
            
            for _ in range(2): # Retry twice
                for selector in switch_selectors:
                    try:
                        switch_btn = driver.find_element(By.XPATH, selector)
                        driver.execute_script("arguments[0].click();", switch_btn)
                        print_lg("Successfully requested classic search mode via UI.")
                        sleep(5) # Wait for reload
                        return
                    except:
                        continue
                sleep(2) # Wait a bit before second retry
                
            print_lg("Warning: Could not find 'Switch back to classic' button, attempting to continue with beta layout.")
    except Exception as e:
        print_lg(f"Error while checking for classic search mode: {str(e)}")

_sticky_filters_reset_done = False


def reset_sticky_account_filters_once() -> None:
    '''
    LinkedIn stores some job-search filters as sticky per-account preferences
    (notably "Under 10 applicants", "In your network", "Has verifications",
    "Fair Chance Employer"). URL params like f_EBP=false are silently dropped,
    so the only way to enforce them OFF is to open the "All filters" modal,
    inspect each toggle's aria-checked state, and click it off if it's ON.

    Runs at most once per bot run (first search term only) to avoid reopening
    the modal for every keyword.
    '''
    global _sticky_filters_reset_done
    if _sticky_filters_reset_done:
        return
    _sticky_filters_reset_done = True

    # Desired state per toggle. True = must be ON, False = must be OFF.
    # Keys are the exact fieldset/h3 labels LinkedIn uses.
    desired_state: dict[str, bool] = {
        "Under 10 applicants": bool(globals().get("under_10_applicants", False)),
        "In your network": bool(globals().get("in_your_network", False)),
        "Fair Chance Employer": bool(globals().get("fair_chance_employer", False)),
        # Easy Apply: if the user wants it (easy_apply_only=True in config), we
        # enforce it ON here too — URL's f_EA=true is silently dropped by
        # LinkedIn for some logged-in accounts, so the UI toggle is the source
        # of truth.
        "Easy Apply": bool(globals().get("easy_apply_only", True)),
    }

    try:
        all_filters_xp = (
            '//button[normalize-space()="All filters"] | '
            '//button[contains(@aria-label,"All filters")] | '
            '//button[contains(@class,"all-filters")]'
        )
        btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, all_filters_xp))
        )
        btn.click()
        buffer(2)

        flipped_any = False
        for label, want_on in desired_state.items():
            try:
                switch = driver.find_element(
                    By.XPATH,
                    f'//h3[normalize-space()="{label}"]/ancestor::fieldset'
                    f'//input[@role="switch"]'
                )
                checked = (switch.get_attribute("aria-checked") or "").lower() == "true"
                dbg(
                    f"Sticky filter '{label}' currently {'ON' if checked else 'OFF'}"
                    f" (desired: {'ON' if want_on else 'OFF'})"
                )
                if checked != want_on:
                    scroll_to_view(driver, switch)
                    actions.move_to_element(switch).click().perform()
                    buffer(click_gap)
                    flipped_any = True
                    print_lg(f"[INFO] Flipped sticky filter '{label}' -> {'ON' if want_on else 'OFF'}.")
            except Exception as tog_err:
                dbg(f"Could not read/flip sticky toggle '{label}': {tog_err}")

        # Click "Show results" / "Apply" to commit. Use broad selector because
        # the label is "Show 123 results" with a dynamic count.
        show_xp = (
            '//button[contains(@aria-label,"Apply current filters")] | '
            '//button[.//span[starts-with(normalize-space(.),"Show")]]'
        )
        try:
            show_btn = WebDriverWait(driver, 4).until(
                EC.element_to_be_clickable((By.XPATH, show_xp))
            )
            show_btn.click()
            buffer(2)
        except Exception as show_err:
            dbg(f"Could not click 'Show results' after sticky reset: {show_err}")
            # Fallback: hit ESC so the modal closes and we don't wedge the page.
            try:
                actions.send_keys(u'\ue00c').perform()  # ESC
            except Exception:
                pass

        if flipped_any:
            print_lg("[INFO] Sticky filter reset complete.")
    except Exception as e:
        print_lg(f"[WARN] Sticky filter reset skipped (All filters button not found): {e}")


def apply_filters() -> None:
    '''
    Function to apply job search filters
    '''
    set_search_location()

    # Resilience mode: all filters are already encoded in the search URL by
    # build_linkedin_jobs_search_url (f_EA, f_WT, sortBy, f_TPR, f_JT, f_E).
    # Skip the filter UI entirely so LinkedIn DOM drift (classic vs pill layout)
    # cannot block the run.
    if globals().get("use_url_filters_only", True):
        dbg("Filter UI skipped; using URL-level filters (use_url_filters_only=True).")
        # Fix sticky account-level toggles (Under 10 applicants, Easy Apply) AFTER
        # URL nav, since LinkedIn can re-apply its per-account sticky prefs on top.
        reset_sticky_account_filters_once()
        return

    ensure_classic_search()

    try:
        recommended_wait = 1 if click_gap < 1 else 0

        # Try multiple selectors for "All filters" button
        filter_button_selectors = [
            '//button[normalize-space()="All filters"]',
            '//button[contains(@class, "all-filters-pill-button")]',
            '//button[@aria-label="All filters"]'
        ]
        
        applied = False
        for selector in filter_button_selectors:
            try:
                button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                button.click()
                applied = True
                break
            except:
                continue
        
        # Fallback for AI-Beta layout: Click individual pills if "All filters" is missing
        if not applied:
            print_lg("Classic 'All filters' not found. Checking for layout-specific pills...")
            # Check for specific pills that exist in Beta (e.g. Easy Apply, Date Posted)
            beta_pills = [
                "//button[contains(., 'Easy Apply')]",
                "//button[contains(., 'Date posted')]",
                "//button[contains(., 'Experience level')]"
            ]
            for pill in beta_pills:
                ele = try_xp(driver, pill, False)
                if ele:
                    print_lg(f"Detected pill-based layout. Attempting to apply filters via individual pills.")
                    applied = True # Consider it 'partially' working/reachable
                    break
                    
        if not applied:
            raise TimeoutException("Could not find 'All filters' button or layout-specific pills")

        buffer(3) # Increased buffer for filter panel loading

        wait_span_click(driver, sort_by)
        wait_span_click(driver, date_posted)
        buffer(recommended_wait)

        multi_sel_noWait(driver, experience_level) 
        multi_sel_noWait(driver, companies, actions)
        if experience_level or companies: buffer(recommended_wait)

        multi_sel_noWait(driver, job_type)
        multi_sel_noWait(driver, on_site)
        if job_type or on_site: buffer(recommended_wait)

        if easy_apply_only: toggle_switch(driver, actions, "Easy Apply")
        
        multi_sel_noWait(driver, location)
        multi_sel_noWait(driver, industry)
        if location or industry: buffer(recommended_wait)

        multi_sel_noWait(driver, job_function)
        multi_sel_noWait(driver, job_titles)
        if job_function or job_titles: buffer(recommended_wait)

        if under_10_applicants: toggle_switch(driver, actions, "Under 10 applicants")
        if in_your_network: toggle_switch(driver, actions, "In your network")
        if fair_chance_employer: toggle_switch(driver, actions, "Fair Chance Employer")

        wait_span_click(driver, salary)
        buffer(recommended_wait)
        
        multi_sel_noWait(driver, benefits)
        multi_sel_noWait(driver, commitments)
        if benefits or commitments: buffer(recommended_wait)

        try:
            show_results_button: WebElement = driver.find_element(By.XPATH, '//button[contains(normalize-space(.), "results")]')
        except:
            show_results_button: WebElement = driver.find_element(By.XPATH, '//button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "apply current filters to show")]')
        
        scroll_to_view(driver, show_results_button)
        buffer(1) # Allow UI to settle
        try:
            show_results_button.click()
        except:
            driver.execute_script("arguments[0].click();", show_results_button)

        global pause_after_filters
        if pause_after_filters and "Turn off Pause after search" == smart_confirm("These are your configured search results and filter. It is safe to change them while this dialog is open, any changes later could result in errors and skipping this search run.", "Please check your results", ["Turn off Pause after search", "Look's good, Continue"]):
            pause_after_filters = False

    except Exception as e:
        print_lg(f"Setting the preferences failed! Falling back to URL-level filters. ERROR: {e}")
        # No blocking confirm dialog: URL already carries f_EA, f_WT, sortBy, f_TPR, f_JT, f_E.

    # Fix sticky account-level toggles AFTER any UI filter work, since LinkedIn
    # may revert them when the results page reloads.
    reset_sticky_account_filters_once()



def get_page_info() -> tuple[WebElement | None, int | None]:
    '''
    Function to get pagination element and current page number
    '''
    try:
        pagination_element = try_find_by_classes(driver, ["jobs-search-pagination__pages", "artdeco-pagination", "artdeco-pagination__pages"])
        if pagination_element:
            scroll_to_view(driver, pagination_element)
            current_page = int(pagination_element.find_element(By.XPATH, "//button[contains(@class, 'active')]").text)
        else:
            print_lg("Pagination element not found, likely single page or UI change.")
            current_page = 1
    except Exception as e:
        print_lg("Failed to find Pagination element info!")
        pagination_element = None
        current_page = None
    return pagination_element, current_page



def get_job_main_details(job: WebElement, blacklisted_companies: set, rejected_jobs: set) -> tuple[str, str, str, str, str, bool]:
    '''
    # Function to get job main details.
    Returns a tuple of (job_id, title, company, work_location, work_style, skip)
    * job_id: Job ID
    * title: Job title
    * company: Company name
    * work_location: Work location of this job
    * work_style: Work style of this job (Remote, On-site, Hybrid)
    * skip: A boolean flag to skip this job
    '''
    try:
        skip = False
        job_details_button = job.find_element(By.TAG_NAME, 'a')  # job.find_element(By.CLASS_NAME, "job-card-list__title")  # Problem in India
        scroll_to_view(driver, job_details_button, True)
        job_id = job.get_dom_attribute('data-occludable-job-id')
        title = job_details_button.text
        title = title[:title.find("\n")]
        # company = job.find_element(By.CLASS_NAME, "job-card-container__primary-description").text
        # work_location = job.find_element(By.CLASS_NAME, "job-card-container__metadata-item").text
        other_details = job.find_element(By.CLASS_NAME, 'artdeco-entity-lockup__subtitle').text
        index = other_details.find(' · ')
        company = other_details[:index]
        work_location = other_details[index+3:]
        work_style = work_location[work_location.rfind('(')+1:work_location.rfind(')')]
        work_location = work_location[:work_location.rfind('(')].strip()
        
        # Skip if previously rejected due to blacklist or already applied
        if company in blacklisted_companies:
            print_lg(f'Skipping "{title} | {company}" job (Blacklisted Company). Job ID: {job_id}!')
            skip = True
        elif job_id in rejected_jobs: 
            print_lg(f'Skipping previously rejected "{title} | {company}" job. Job ID: {job_id}!')
            skip = True
        try:
            if job.find_element(By.CLASS_NAME, "job-card-container__footer-job-state").text == "Applied":
                skip = True
                print_lg(f'Already applied to "{title} | {company}" job. Job ID: {job_id}!')
        except: pass
        try: 
            if not skip: 
                # Try clicking via JS as click() is sometimes intercepted
                driver.execute_script("arguments[0].click();", job_details_button)
        except Exception as e:
            print_lg(f'Failed to click "{title} | {company}" job on details button. Job ID: {job_id}!') 
            discard_job()
            skip = True
        buffer(click_gap)
        return (job_id,title,company,work_location,work_style,skip)
    except Exception as e:
        try:
            job_id = job.get_dom_attribute('data-occludable-job-id')
            print_lg(f"Error fetching main details for Job ID {job_id}: {str(e)[:100]}")
        except:
            print_lg(f"Error fetching main details for a job (stale or missing): {str(e)[:100]}")
        return ("", "", "", "", "", True)


# Function to check for Blacklisted words in About Company
def check_blacklist(rejected_jobs: set, job_id: str, company: str, blacklisted_companies: set) -> tuple[set, set, WebElement] | ValueError:
    jobs_top_card = try_find_by_classes(driver, ["job-details-jobs-unified-top-card__primary-description-container","job-details-jobs-unified-top-card__primary-description","jobs-unified-top-card__primary-description","jobs-details__main-content","jobs-details__top-card","jobs-unified-top-card"])
    if jobs_top_card is None:
        dbg("No jobs_top_card class matched; LinkedIn DOM may have changed. Proceeding without blacklist scroll.")
    about_company_org = find_by_class(driver, "jobs-company__box")
    if about_company_org:
        scroll_to_view(driver, about_company_org)
        about_company_org = about_company_org.text
    else:
        about_company_org = ""
    about_company = about_company_org.lower()
    skip_checking = False
    for word in about_company_good_words:
        if word.lower() in about_company:
            print_lg(f'Found the word "{word}". So, skipped checking for blacklist words.')
            skip_checking = True
            break
    if not skip_checking:
        for word in about_company_bad_words: 
            if word.lower() in about_company: 
                rejected_jobs.add(job_id)
                blacklisted_companies.add(company)
                raise ValueError(f'\n"{about_company_org}"\n\nContains "{word}".')
    buffer(click_gap)
    if jobs_top_card is not None:
        try:
            scroll_to_view(driver, jobs_top_card)
        except Exception as scroll_err:
            dbg(f"scroll_to_view failed: {scroll_err}")
    return rejected_jobs, blacklisted_companies, jobs_top_card



# Function to extract years of experience required from About Job
def extract_years_of_experience(text: str) -> int:
    # Extract all patterns like '10+ years', '5 years', '3-5 years', etc.
    matches = re.findall(re_experience, text)
    if len(matches) == 0: 
        print_lg(f'\n{text}\n\nCouldn\'t find experience requirement in About the Job!')
        return 0
    return max([int(match) for match in matches if int(match) <= 12])



def get_job_description(
) -> tuple[
    str | Literal['Unknown'],
    int | Literal['Unknown'],
    bool,
    str | None,
    str | None
    ]:
    '''
    # Job Description
    Function to extract job description from About the Job.
    ### Returns:
    - `jobDescription: str | 'Unknown'`
    - `experience_required: int | 'Unknown'`
    - `skip: bool`
    - `skipReason: str | None`
    - `skipMessage: str | None`
    '''
    jobDescription = "Unknown"
    experience_required = "Unknown"
    skip = False
    skipReason = None
    skipMessage = None
    try:
        found_masters = 0
        jobDescription = find_by_class(driver, "jobs-box__html-content").text
        jobDescriptionLow = jobDescription.lower()
        for word in bad_words:
            if word.lower() in jobDescriptionLow:
                skipMessage = f'\n{jobDescription}\n\nContains bad word "{word}". Skipping this job!\n'
                skipReason = "Found a Bad Word in About Job"
                skip = True
                break
        if not skip and security_clearance == False and ('polygraph' in jobDescriptionLow or 'clearance' in jobDescriptionLow or 'secret' in jobDescriptionLow):
            skipMessage = f'\n{jobDescription}\n\nFound "Clearance" or "Polygraph". Skipping this job!\n'
            skipReason = "Asking for Security clearance"
            skip = True
        if not skip:
            if did_masters and 'master' in jobDescriptionLow:
                print_lg(f'Found the word "master" in \n{jobDescription}')
                found_masters = 2
            experience_required = extract_years_of_experience(jobDescription)
            if current_experience > -1 and experience_required > current_experience + found_masters:
                skipMessage = f'\n{jobDescription}\n\nExperience required {experience_required} > Maximum Experience {current_experience + found_masters}. Skipping this job!\n'
                skipReason = "Required experience is high"
                skip = True
            elif min_experience > 0 and experience_required > 0 and experience_required < min_experience:
                skipMessage = f'\n{jobDescription}\n\nExperience required {experience_required} < Minimum Experience {min_experience}. Skipping this job!\n'
                skipReason = "Required experience is low"
                skip = True
    except Exception as e:
        if jobDescription == "Unknown":    print_lg("Unable to extract job description!")
        else:
            experience_required = "Error in extraction"
            print_lg("Unable to extract years of experience required!")
            # print_lg(e)
    
    return jobDescription, experience_required, skip, skipReason, skipMessage
        


def _easy_apply_location_text_answer(work_location: str) -> str:
    '''
    Prefer a full "City, State, Country" line from job-search config when set,
    so the Easy Apply typeahead matches LinkedIn\'s first suggestion (e.g.
    "Noida, Uttar Pradesh, India") instead of stopping on "Noida" and missing
    the dropdown commit.
    '''
    sl = (search_location or "").strip()
    cc = (current_city or "").strip()
    wl = (work_location or "").strip()
    if sl and "," in sl:
        return sl
    if cc:
        return cc
    return wl or cc


def _collect_visible_typeahead_options(driver, modal: WebElement | None) -> list[WebElement]:
    '''
    Options may render inside the modal, in an artdeco popover, or in a
    partner (e.g. PyjamaHR) subtree — try modal-scoped XPaths first, then
    Easy-Apply–scoped global XPaths so we don\'t grab the jobs search bar list.
    '''
    seen: set[int] = set()
    out: list[WebElement] = []

    def add_from(root: WebDriver | WebElement, xps: list[str], relative: bool) -> None:
        for xp in xps:
            try:
                els = root.find_elements(By.XPATH, xp if relative else xp)
                for el in els:
                    try:
                        if not el.is_displayed():
                            continue
                    except Exception:
                        continue
                    eid = id(el)
                    if eid in seen:
                        continue
                    seen.add(eid)
                    out.append(el)
            except Exception:
                continue

    modal_xps = [
        ".//*[@role='listbox']//*[@role='option']",
        ".//li[@role='option']",
        ".//div[@role='option']",
    ]
    global_xps = [
        "//div[contains(@class,'jobs-easy-apply-modal')]//*[@role='listbox']//*[@role='option']",
        "//div[contains(@class,'jobs-easy-apply-modal')]//li[@role='option']",
        "//div[contains(@class,'jobs-easy-apply-content')]//*[@role='listbox']//*[@role='option']",
        "//*[contains(@class,'artdeco-typeahead')]//*[@role='option']",
        "//div[contains(@class,'basic-typeahead')]//li[@role='option']",
        "//ul[@role='listbox']//li[@role='option']",
        "//*[@role='listbox']//*[@role='option']",
    ]
    if modal is not None:
        add_from(modal, modal_xps, True)
    add_from(driver, global_xps, False)
    return out


def commit_typeahead_choice(
    modal: WebElement | None,
    text_input: WebElement,
    typed_value: str,
    label_org: str,
) -> None:
    '''
    Commit a value into a LinkedIn typeahead/autocomplete input (e.g. the
    "Location (city)" field that shows "Noida" -> dropdown with "Noida,
    Uttar Pradesh, India" etc.).

    LinkedIn renders three typeahead variants in Easy Apply forms:
      - "basic-typeahead" (classic)
      - "artdeco-typeahead" (LEGO / newer)
      - Ember-based listbox with role="option"

    All three:
      * show options as `role="option"` (or `<li>` under
        `ul[role="listbox"]`) that react to mouse click, NOT always to
        keyboard Enter on the input.
      * load options asynchronously after a debounced network call, so a
        fixed `sleep()` is not reliable.

    Strategy (in order; first one that commits wins):
      1. Poll up to ~6s for option elements (modal-scoped, then Easy Apply
         global) so we don\'t steal the jobs search-bar suggestions.
      2. Rank options (prefer "Noida, Uttar Pradesh" over "Greater Noida").
      3. Click the best option directly.
      4. Fallback: keyboard ArrowDown + Enter on the input itself.
      5. Verify the input value; warn if unchanged.
    '''
    deadline = time.time() + 6.0
    options: list[WebElement] = []
    while time.time() < deadline and not options:
        options = _collect_visible_typeahead_options(driver, modal)
        if not options:
            sleep(0.2)

    chosen: WebElement | None = None
    if options:
        texts: list[str] = []
        for o in options:
            try:
                texts.append((o.text or "").strip())
            except Exception:
                texts.append("")
        best_i = pick_best_typeahead_index(typed_value, texts)
        chosen = options[best_i]

    if chosen is not None:
        try:
            scroll_to_view(driver, chosen)
            # Direct click works across all three typeahead variants.
            chosen.click()
            sleep(0.4)
        except ElementClickInterceptedException:
            # Something overlays it; try JS click as a last resort.
            try:
                driver.execute_script("arguments[0].click();", chosen)
                sleep(0.4)
            except Exception as js_err:
                dbg(f"typeahead JS click failed for '{label_org}': {js_err}")
        except Exception as click_err:
            dbg(f"typeahead option click failed for '{label_org}': {click_err}")
    else:
        # Keyboard fallback — only helps for native-select-like widgets.
        dbg(f"No typeahead options appeared for '{label_org}'; trying keyboard fallback.")
        try:
            text_input.send_keys(Keys.ARROW_DOWN)
            sleep(0.3)
            text_input.send_keys(Keys.ENTER)
        except Exception as kb_err:
            dbg(f"typeahead keyboard fallback failed for '{label_org}': {kb_err}")

    # Verification: after commit, the input should hold a non-empty committed
    # value. For LinkedIn typeaheads the value often expands to include
    # state/country (e.g. "Noida, Uttar Pradesh, India"). Log if it didn't.
    try:
        committed = (text_input.get_attribute("value") or "").strip()
        if not committed:
            print_lg(f"[WARN] Typeahead '{label_org}' input is empty after commit attempt.")
        elif committed.lower() == (typed_value or "").strip().lower() and options:
            # Typed value never expanded — may mean option wasn't committed.
            dbg(f"Typeahead '{label_org}' value '{committed}' unchanged after click; dropdown may not have committed.")
    except Exception:
        pass


def get_active_modal(timeout: float = 5.0) -> WebElement:
    '''
    Always return the currently-live Easy Apply modal WebElement.

    LinkedIn re-renders the modal DOM between Next/Review/Submit steps, so any
    cached reference from a previous step is `StaleElementReferenceException`
    the moment you touch it. Call this at the top of every iteration instead
    of caching.
    '''
    try:
        return WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".jobs-easy-apply-modal, .artdeco-modal"))
        )
    except Exception:
        return WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'modal')]//button[contains(@aria-label, 'Dismiss')]/../.."))
        )


def _find_next_or_review_or_submit(modal: WebElement) -> WebElement:
    '''
    Locate the active "Next" / "Review" / "Submit application" / "Continue"
    button inside the given modal. Selectors are tried in the same order
    as before (Review/Submit preferred over Next) so behavior is unchanged.
    Raises NoSuchElementException if none match.
    '''
    xps = [
        './/button[contains(@aria-label, "Review") or contains(@aria-label, "Submit")]',
        './/button[.//span[contains(normalize-space(.), "Review") or contains(normalize-space(.), "Submit")]]',
        './/button[contains(span, "Next")]',
        './/button[@aria-label="Continue to next step"]',
        './/button[contains(@aria-label, "Continue")]',
    ]
    last_err: Exception | None = None
    for xp in xps:
        try:
            return modal.find_element(By.XPATH, xp)
        except NoSuchElementException as e:
            last_err = e
            continue
    raise last_err if last_err else NoSuchElementException("No Next/Review/Submit button found")


def _click_submit_easy_apply_final() -> bool:
    '''
    Click Submit inside the Easy Apply modal using modal-scoped XPaths first.
    Avoids matching unrelated "Submit" buttons elsewhere on the page and reduces
    false negatives when LinkedIn uses slightly different labels/aria text.
    '''
    try:
        modal = get_active_modal(4)
    except Exception:
        return bool(wait_span_click(driver, "Submit application", 2, scrollTop=True)) or bool(wait_span_click(driver, "Submit", 2, scrollTop=True))
    xps = [
        './/button[contains(normalize-space(.), "Submit application")]',
        './/button[.//span[contains(normalize-space(.), "Submit application")]]',
        './/button[contains(@aria-label, "Submit application")]',
        './/button[contains(@aria-label, "Submit your application")]',
        './/button[normalize-space(.)="Submit"]',
        './/button[.//span[normalize-space(.)="Submit"]]',
        './/button[@aria-label="Submit"]',
        './/button[contains(normalize-space(.), "Post")]',
        './/button[contains(normalize-space(.), "Submit")]',
    ]
    for xp in xps:
        try:
            btn = modal.find_element(By.XPATH, xp)
            if not btn.is_displayed():
                continue
            scroll_to_view(driver, btn, True)
            try:
                btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();", btn)
            buffer(click_gap)
            return True
        except (NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException):
            continue
        except Exception:
            continue
    
    # FINAL CATCH-ALL: Search all buttons in modal for any matching keyword
    try:
        btns = modal.find_elements(By.TAG_NAME, "button")
        for b in btns:
            txt = (b.text or b.get_attribute("aria-label") or "").lower()
            if any(k in txt for k in ["submit", "post", "done"]):
                if b.is_displayed():
                    scroll_to_view(driver, b, True)
                    driver.execute_script("arguments[0].click();", b)
                    print_lg(f"[INFO] Clicked fallback submit button: {txt}")
                    return True
    except Exception:
        pass
        
    print_lg("Click Failed! Didn't find 'Submit application'")
    screenshot(driver, "SUBMIT_FAILURE", "Failed to find submit button")
    return False


def _reinit_browser_with_retry(max_attempts: int = 3, pause_s: float = 5.0) -> tuple:
    '''
    Rebuild a fresh Chrome session after a crash. Tries up to `max_attempts`
    times because `session not created: DevToolsActivePort file doesn't exist`
    typically passes on the 2nd try.

    Before each attempt we teardown the dead driver and sweep zombie
    chromedriver/headless-chrome processes so the next spawn isn't blocked by
    a lock file or orphaned process.

    Returns (options, driver, actions, wait) on success; re-raises the last
    exception after `max_attempts` failures.
    '''
    global driver
    last_err: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            try:
                if driver is not None:
                    driver.quit()
            except Exception:
                pass
            try:
                cleanup_zombie_processes()
            except Exception:
                pass
            print_lg(f"[INFO] Re-init attempt {attempt}/{max_attempts}...")
            options, new_driver, actions, wait = init_browser()
            print_lg(f"[INFO] Re-init attempt {attempt}/{max_attempts} succeeded.")
            return options, new_driver, actions, wait
        except Exception as e:
            last_err = e
            print_lg(f"[WARN] Re-init attempt {attempt}/{max_attempts} failed: {e}")
            if attempt < max_attempts:
                sleep(pause_s)
    raise last_err if last_err else RuntimeError("Re-init failed with no captured exception")


# Function to upload resume
def upload_resume(modal: WebElement, resume: str) -> tuple[bool, str]:
    try:
        modal.find_element(By.NAME, "file").send_keys(os.path.abspath(resume))
        return True, os.path.basename(default_resume_path)
    except: return False, "Previous resume"

# Function to check for custom answers from configuration
def get_custom_answer(label: str) -> str | None:
    '''
    Checks the custom_answers dictionary for keywords in the label.
    Returns the answer if found, else None.
    '''
    label_lower = label.lower()
    for keyword, value in custom_answers.items():
        if keyword.lower() in label_lower:
            return str(value)
    return None

def save_questions_to_custom_config(questions_list: set) -> None:
    '''
    Appends new questions from questions_list to config/custom_questions.py
    '''
    config_path = "config/custom_questions.py"
    if not os.path.exists(config_path): 
        print_lg(f"Config file {config_path} not found. Skipping save.")
        return
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "custom_answers = {" not in content: 
            print_lg("Could not find 'custom_answers' dictionary in config.")
            return
        
        last_brace_index = content.rfind("}")
        if last_brace_index == -1: return
        
        new_entries = []
        for q_data in questions_list:
            if not q_data or len(q_data) < 2: continue
            label = q_data[0]
            answer = q_data[1]
            
            # Clean label of metadata we might have added
            clean_label = label.split(" [ ")[0].split(" (")[0].strip()
            if not clean_label or clean_label.lower() in ["unknown", ""]: continue
            
            # Avoid duplicates by checking lower case label
            if f'"{clean_label.lower()}":' not in content.lower() and f"'{clean_label.lower()}':" not in content.lower():
                new_entries.append(f'    "{clean_label}": "{answer}",')
        
        if new_entries:
            updated_content = content[:last_brace_index].rstrip() + "\n" + "\n".join(new_entries) + "\n" + content[last_brace_index:]
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(updated_content)
            print_lg(f"--- LEARNING MODE: Saved {len(new_entries)} new questions to {config_path} ---")
            
    except Exception as e:
        print_lg(f"Failed to save questions to config: {e}")

# Function to answer common questions for Easy Apply
def answer_common_questions(label: str, answer: str) -> str:
    if 'sponsorship' in label or 'visa' in label: answer = require_visa
    return answer


# Function to answer the questions for Easy Apply
def fill_easy_apply_form(modal: WebElement, questions_list: set, work_location: str, job_description: str | None = None ) -> set:
    # Get all questions from the page
     
    all_questions = modal.find_elements(By.XPATH, ".//div[@data-test-form-element]")
    # all_questions = modal.find_elements(By.CLASS_NAME, "jobs-easy-apply-form-element")
    # all_list_questions = modal.find_elements(By.XPATH, ".//div[@data-test-text-entity-list-form-component]")
    # all_single_line_questions = modal.find_elements(By.XPATH, ".//div[@data-test-single-line-text-form-component]")
    # all_questions = all_questions + all_list_questions + all_single_line_questions

    for Question in all_questions:
        # Check if it's a select Question
        select = try_xp(Question, ".//select", False)
        if select:
            label_org = "Unknown"
            try:
                label = Question.find_element(By.TAG_NAME, "label")
                label_org = label.find_element(By.TAG_NAME, "span").text
            except: pass
            answer = 'Yes'
            label = label_org.lower()
            select = Select(select)
            selected_option = select.first_selected_option.text
            optionsText = []
            options = '"List of phone country codes"'
            if label != "phone country code":
                optionsText = [option.text for option in select.options]
                options = "".join([f' "{option}",' for option in optionsText])
            prev_answer = selected_option
            if overwrite_previous_answers or selected_option == "Select an option":
                ##> ------ WINDY_WINDWARD Email:karthik.sarode23@gmail.com - Added fuzzy logic to answer location based questions ------
                if 'email' in label or 'phone' in label: 
                    answer = prev_answer
                elif 'gender' in label or 'sex' in label: 
                    answer = gender
                elif 'disability' in label: 
                    answer = disability_status
                elif 'proficiency' in label: 
                    answer = 'Professional'
                # Add location handling
                elif any(loc_word in label for loc_word in ['location', 'city', 'state', 'country']):
                    if 'country' in label:
                        answer = country 
                    elif 'state' in label:
                        answer = state
                    elif 'city' in label:
                        answer = _easy_apply_location_text_answer(work_location)
                    else:
                        answer = _easy_apply_location_text_answer(work_location)
                else: 
                    custom_answer = get_custom_answer(label)
                    if custom_answer:
                        answer = custom_answer
                    else:
                        answer = answer_common_questions(label,answer)
                try: 
                    select.select_by_visible_text(answer)
                except NoSuchElementException as e:
                    # Define similar phrases for common answers
                    possible_answer_phrases = []
                    if answer == 'Decline':
                        possible_answer_phrases = ["Decline", "not wish", "don't wish", "Prefer not", "not want"]
                    elif 'yes' in answer.lower():
                        possible_answer_phrases = ["Yes", "Agree", "I do", "I have"]
                    elif 'no' in answer.lower():
                        possible_answer_phrases = ["No", "Disagree", "I don't", "I do not"]
                    else:
                        # Try partial matching for any answer
                        possible_answer_phrases = [answer]
                        # Add lowercase and uppercase variants
                        possible_answer_phrases.append(answer.lower())
                        possible_answer_phrases.append(answer.upper())
                        # Try without special characters
                        possible_answer_phrases.append(''.join(c for c in answer if c.isalnum()))
                    ##<
                    foundOption = False
                    for phrase in possible_answer_phrases:
                        for option in optionsText:
                            # Check if phrase is in option or option is in phrase (bidirectional matching)
                            if phrase.lower() in option.lower() or option.lower() in phrase.lower():
                                select.select_by_visible_text(option)
                                answer = option
                                foundOption = True
                                break
                    if not foundOption:
                        #TODO: Use AI to answer the question need to be implemented logic to extract the options for the question
                        print_lg(f'Failed to find an option with text "{answer}" for question labelled "{label_org}", answering randomly!')
                        select.select_by_index(randint(1, len(select.options)-1))
                        answer = select.first_selected_option.text
                        randomly_answered_questions.add((f'{label_org} [ {options} ]',"select"))
            questions_list.add((f'{label_org} [ {options} ]', answer, "select", prev_answer))
            continue
        
        # Check if it's a radio Question
        radio = try_xp(Question, './/fieldset[@data-test-form-builder-radio-button-form-component="true"]', False)
        if radio:
            prev_answer = None
            label = try_xp(radio, './/span[@data-test-form-builder-radio-button-form-component__title]', False)
            try: label = find_by_class(label, "visually-hidden", 2.0)
            except: pass
            label_org = label.text if label else "Unknown"
            answer = 'Yes'
            label = label_org.lower()

            label_org += ' [ '
            options = radio.find_elements(By.TAG_NAME, 'input')
            options_labels = []
            
            for option in options:
                id = option.get_attribute("id")
                option_label = try_xp(radio, f'.//label[@for="{id}"]', False)
                options_labels.append( f'"{option_label.text if option_label else "Unknown"}"<{option.get_attribute("value")}>' ) # Saving option as "label <value>"
                if option.is_selected(): prev_answer = options_labels[-1]
                label_org += f' {options_labels[-1]},'

            if overwrite_previous_answers or prev_answer is None:
                if 'citizenship' in label or 'employment eligibility' in label: answer = us_citizenship
                elif 'veteran' in label or 'protected' in label: answer = veteran_status
                elif 'disability' in label or 'handicapped' in label: 
                    answer = disability_status
                else: 
                    custom_answer = get_custom_answer(label)
                    if custom_answer:
                        answer = custom_answer
                    else:
                        answer = answer_common_questions(label,answer)
                foundOption = try_xp(radio, f".//label[normalize-space()='{answer}']", False)
                if foundOption: 
                    actions.move_to_element(foundOption).click().perform()
                else:    
                    possible_answer_phrases = ["Decline", "not wish", "don't wish", "Prefer not", "not want"] if answer == 'Decline' else [answer]
                    ele = options[0]
                    answer = options_labels[0]
                    for phrase in possible_answer_phrases:
                        for i, option_label in enumerate(options_labels):
                            if phrase in option_label:
                                foundOption = options[i]
                                ele = foundOption
                                answer = f'Decline ({option_label})' if len(possible_answer_phrases) > 1 else option_label
                                break
                        if foundOption: break
                    # if answer == 'Decline':
                    #     answer = options_labels[0]
                    #     for phrase in ["Prefer not", "not want", "not wish"]:
                    #         foundOption = try_xp(radio, f".//label[normalize-space()='{phrase}']", False)
                    #         if foundOption:
                    #             answer = f'Decline ({phrase})'
                    #             ele = foundOption
                    #             break
                    actions.move_to_element(ele).click().perform()
                    if not foundOption: randomly_answered_questions.add((f'{label_org} ]',"radio"))
            else: answer = prev_answer
            questions_list.add((label_org+" ]", answer, "radio", prev_answer))
            continue
        
        # Check if it's a text question
        text = try_xp(Question, ".//input[@type='text']", False)
        if text: 
            do_actions = False
            label = try_xp(Question, ".//label[@for]", False)
            try: label = label.find_element(By.CLASS_NAME,'visually-hidden')
            except: pass
            label_org = label.text if label else "Unknown"
            answer = "" # years_of_experience
            label = label_org.lower()

            prev_answer = text.get_attribute("value")
            if not prev_answer or overwrite_previous_answers:
                custom_answer = get_custom_answer(label)
                if custom_answer:
                    answer = custom_answer
                elif 'experience' in label or 'years' in label: answer = years_of_experience
                elif 'phone' in label or 'mobile' in label: answer = phone_number
                elif 'street' in label: answer = street
                elif 'city' in label or 'location' in label or 'address' in label:
                    answer = _easy_apply_location_text_answer(work_location)
                    do_actions = True
                elif 'signature' in label: answer = full_name # 'signature' in label or 'legal name' in label or 'your name' in label or 'full name' in label: answer = full_name     # What if question is 'name of the city or university you attend, name of referral etc?'
                elif 'name' in label:
                    if 'full' in label: answer = full_name
                    elif 'first' in label and 'last' not in label: answer = first_name
                    elif 'middle' in label and 'last' not in label: answer = middle_name
                    elif 'last' in label and 'first' not in label: answer = last_name
                    elif 'employer' in label: answer = recent_employer
                    else: answer = full_name
                elif 'notice' in label:
                    if 'month' in label:
                        answer = notice_period_months
                    elif 'week' in label:
                        answer = notice_period_weeks
                    else: answer = notice_period
                elif 'salary' in label or 'compensation' in label or 'ctc' in label or 'pay' in label: 
                    if 'current' in label or 'present' in label:
                        if 'month' in label:
                            answer = current_ctc_monthly
                        elif 'lakh' in label:
                            answer = current_ctc_lakhs
                        else:
                            answer = current_ctc
                    else:
                        if 'month' in label:
                            answer = desired_salary_monthly
                        elif 'lakh' in label:
                            answer = desired_salary_lakhs
                        else:
                            answer = desired_salary
                elif 'linkedin' in label: answer = linkedIn
                elif 'website' in label or 'blog' in label or 'portfolio' in label or 'link' in label: answer = website
                elif 'scale of 1-10' in label: answer = confidence_level
                elif 'headline' in label: answer = linkedin_headline
                elif ('hear' in label or 'come across' in label) and 'this' in label and ('job' in label or 'position' in label): answer = "LinkedIn"
                elif 'state' in label or 'province' in label: answer = state
                elif 'zip' in label or 'postal' in label or 'code' in label: answer = zipcode
                elif 'country' in label: answer = country
                else: answer = answer_common_questions(label,answer)
                ##> ------ Yang Li : MARKYangL - Feature ------
                if answer == "":
                    ai_answer = ai_text_answer('answer_question', aiClient, label_org, options=None, question_type="text", job_description=job_description, about_company=None, user_information_all=user_information_all) if use_AI else ""
                    if ai_answer:
                        answer = ai_answer
                        print_lg(f'AI Answered received for question "{label_org}" \nhere is answer: "{answer}"')
                    else:
                        randomly_answered_questions.add((label_org, "text"))
                        answer = years_of_experience
                ##<
                text.clear()
                text.send_keys(str(answer))
                if do_actions:
                    commit_typeahead_choice(modal, text, str(answer), label_org)
            questions_list.add((label, text.get_attribute("value"), "text", prev_answer))
            continue

        # Check if it's a textarea question
        text_area = try_xp(Question, ".//textarea", False)
        if text_area:
            do_actions = False
            label = try_xp(Question, ".//label[@for]", False)
            label_org = label.text if label else "Unknown"
            label = label_org.lower()
            answer = ""
            prev_answer = text_area.get_attribute("value")
            if not prev_answer or overwrite_previous_answers:
                custom_answer = get_custom_answer(label)
                if custom_answer:
                    answer = custom_answer
                elif 'summary' in label: answer = linkedin_summary
                elif 'cover' in label: answer = cover_letter
                elif 'about' in label or 'introduce' in label or 'yourself' in label or 'why' in label:
                    answer = user_information_all
                if answer == "":
                    ai_answer = ai_text_answer('answer_question', aiClient, label_org, options=None, question_type="textarea", job_description=job_description, about_company=None, user_information_all=user_information_all) if use_AI else ""
                    if ai_answer:
                        answer = ai_answer
                        print_lg(f'AI Answered received for question "{label_org}" \nhere is answer: "{answer}"')
                    else:
                        # Offline fallback: reuse the bio instead of leaving the field blank,
                        # which otherwise blocks Submit on required textareas.
                        answer = user_information_all or linkedin_summary or ""
                        randomly_answered_questions.add((label_org, "textarea"))

            text_area.clear()
            text_area.send_keys(str(answer))
            if do_actions:
                    sleep(2)
                    actions.send_keys(Keys.ARROW_DOWN)
                    actions.send_keys(Keys.ENTER).perform()
            questions_list.add((label, text_area.get_attribute("value"), "textarea", prev_answer))
            ##<
            continue

        # Check if it's a checkbox question
        checkbox = try_xp(Question, ".//input[@type='checkbox']", False)
        if checkbox:
            # Do not auto-toggle here — the generic branch always CHECKS unchecked boxes,
            # which would force "Follow company" ON. LinkedIn / partner UIs must only be
            # toggled in follow_company() so we always leave "Follow … stay up to date" OFF.
            cb_id = (checkbox.get_attribute("id") or "").strip()
            try:
                qtext = (Question.get_attribute("innerText") or "").lower()
            except Exception:
                qtext = ""
            if (
                cb_id == "follow-company-checkbox"
                or "follow-company" in cb_id.lower()
                or ("follow" in qtext and "stay up" in qtext)
            ):
                continue
            label = try_xp(Question, ".//span[@class='visually-hidden']", False)
            label_org = label.text if label else "Unknown"
            label = label_org.lower()
            answer = try_xp(Question, ".//label[@for]", False)  # Sometimes multiple checkboxes are given for 1 question, Not accounted for that yet
            answer = answer.text if answer else "Unknown"
            prev_answer = checkbox.is_selected()
            checked = prev_answer
            if not prev_answer:
                try:
                    actions.move_to_element(checkbox).click().perform()
                    checked = True
                except Exception as e: 
                    print_lg("Checkbox click failed!", e)
                    pass
            questions_list.add((f'{label} ([X] {answer})', checked, "checkbox", prev_answer))
            continue


    # LinkedIn / PyjamaHR often default this ON on the review step — force OFF every page.
    try:
        follow_company(modal)
    except Exception as _fc_err:
        dbg(f"follow_company mid-form: {_fc_err}")

    # Select todays date
    try_xp(driver, "//button[contains(@aria-label, 'This is today')]")

    # Collect important skills
    # if 'do you have' in label and 'experience' in label and ' in ' in label -> Get word (skill) after ' in ' from label
    # if 'how many years of experience do you have in ' in label -> Get word (skill) after ' in '

    return questions_list




def external_apply(pagination_element: WebElement, job_id: str, job_link: str, resume: str, date_listed, application_link: str, screenshot_name: str) -> tuple[bool, str, int]:
    '''
    Function to open new tab and save external job application links
    '''
    global tabs_count, dailyEasyApplyLimitReached
    if easy_apply_only:
        try:
            if "exceeded the daily application limit" in driver.find_element(By.CLASS_NAME, "artdeco-inline-feedback__message").text: dailyEasyApplyLimitReached = True
        except: pass
        print_lg("Easy apply failed I guess!")
        if pagination_element != None: return True, application_link, tabs_count
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, ".//button[contains(@class,'jobs-apply-button') and contains(@class, 'artdeco-button--3')]"))).click() # './/button[contains(span, "Apply") and not(span[contains(@class, "disabled")])]'
        wait_span_click(driver, "Continue", 1, True, False)
        windows = driver.window_handles
        tabs_count = len(windows)
        driver.switch_to.window(windows[-1])
        application_link = driver.current_url
        print_lg('Got the external application link "{}"'.format(application_link))
        if close_tabs and driver.current_window_handle != linkedIn_tab: driver.close()
        driver.switch_to.window(linkedIn_tab)
        return False, application_link, tabs_count
    except Exception as e:
        # print_lg(e)
        print_lg("Failed to apply!")
        failed_job(job_id, job_link, resume, date_listed, "Probably didn't find Apply button or unable to switch tabs.", e, application_link, screenshot_name)
        global failed_count
        failed_count += 1
        return True, application_link, tabs_count



def follow_company(modal: WebElement | None = None) -> None:
    '''
    Always uncheck the Easy Apply "Follow <company> … stay up to date" box.

    LinkedIn and third-party flows (e.g. PyjamaHR) may use different ids; we
    probe several XPaths and re-read the modal each attempt because the DOM
    is rebuilt between steps.
    '''
    want = False
    print_lg("[DEBUG] Ensuring 'Follow company' checkbox stays OFF (policy: never follow from Easy Apply).")

    label_xps = [
        ".//label[contains(@for, 'follow-company-checkbox')]",
        ".//label[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'follow') and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'stay up')]",
    ]
    input_xps = [
        ".//input[@id='follow-company-checkbox']",
        ".//input[contains(@id,'follow-company') or contains(@name,'follow-company')]",
        ".//label[contains(.,'Follow') and contains(.,'stay up')]/preceding-sibling::input[@type='checkbox']",
        ".//label[contains(.,'Follow') and contains(.,'stay up')]/following-sibling::input[@type='checkbox']",
        ".//label[contains(.,'Follow') and contains(.,'stay up')]/../input[@type='checkbox']",
        ".//input[@type='checkbox' and (contains(@aria-label,'Follow') or contains(@aria-label,'follow'))]",
    ]
    fallback_cb_xp = (
        ".//input[@type='checkbox' and ("
        "contains(..//span, 'Follow') or contains(..//label, 'Follow') or contains(@aria-label, 'Follow')"
        ")]"
    )

    def _selected(el: WebElement) -> bool:
        try:
            if el.get_attribute("aria-checked") is not None:
                return (el.get_attribute("aria-checked") or "").lower() == "true"
        except Exception:
            pass
        try:
            return bool(el.is_selected())
        except Exception:
            return False

    def _find_checkbox(root: WebElement) -> WebElement | None:
        for xp in input_xps:
            cb = try_xp(root, xp, False)
            if cb:
                return cb
        return try_xp(root, fallback_cb_xp, False)

    for attempt in range(4):
        try:
            try:
                root = get_active_modal(4)
            except Exception:
                root = modal if modal is not None else driver

            cb = _find_checkbox(root)
            if not cb:
                dbg("Follow checkbox not found on this screen.")
                return

            if _selected(cb) == want:
                dbg("Follow company already unchecked.")
                return

            lbl = None
            for lxp in label_xps:
                lbl = try_xp(root, lxp, False)
                if lbl:
                    break
            try:
                scroll_to_view(driver, cb)
                if lbl:
                    driver.execute_script("arguments[0].click();", lbl)
                else:
                    driver.execute_script("arguments[0].click();", cb)
            except Exception:
                try:
                    driver.execute_script("arguments[0].click();", cb)
                except Exception:
                    pass

            buffer(click_gap)
            if _selected(cb) == want:
                print_lg("[INFO] 'Follow company' left unchecked as required.")
                return
        except Exception as e:
            dbg(f"Follow company toggle attempt {attempt} failed: {e}")
    print_lg("[WARNING] Could not verify 'Follow company' unchecked; please check before submit.")
    


#< Failed attempts logging
def failed_job(job_id: str, job_link: str, resume: str, date_listed, error: str, exception: Exception, application_link: str, screenshot_name: str) -> None:
    '''
    Function to update failed jobs list in excel
    '''
    try:
        with open(failed_file_name, 'a', newline='', encoding='utf-8') as file:
            fieldnames = ['Job ID', 'Job Link', 'Resume Tried', 'Date listed', 'Date Tried', 'Assumed Reason', 'Stack Trace', 'External Job link', 'Screenshot Name']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0: writer.writeheader()
            writer.writerow({'Job ID':truncate_for_csv(job_id), 'Job Link':truncate_for_csv(job_link), 'Resume Tried':truncate_for_csv(resume), 'Date listed':truncate_for_csv(date_listed), 'Date Tried':datetime.now(), 'Assumed Reason':truncate_for_csv(error), 'Stack Trace':truncate_for_csv(exception), 'External Job link':truncate_for_csv(application_link), 'Screenshot Name':truncate_for_csv(screenshot_name)})
            file.close()
    except Exception as e:
        print_lg("Failed to update failed jobs list!", e)
        smart_alert("Failed to update the excel of failed jobs!\nProbably because of 1 of the following reasons:\n1. The file is currently open or in use by another program\n2. Permission denied to write to the file\n3. Failed to find the file", "Failed Logging")


def screenshot(driver: WebDriver, job_id: str, failedAt: str) -> str:
    '''
    Function to to take screenshot for debugging
    - Returns screenshot name as String
    '''
    screenshot_name = "{} - {} - {}.png".format( job_id, failedAt, str(datetime.now()) )
    path = "history/screenshots/"+screenshot_name.replace(":",".")
    # special_chars = {'*', '"', '\\', '<', '>', ':', '|', '?'}
    # for char in special_chars:  path = path.replace(char, '-')
    driver.save_screenshot(path.replace("//","/"))
    return screenshot_name
#>



def submitted_jobs(job_id: str, title: str, company: str, work_location: str, work_style: str, description: str, experience_required: int | Literal['Unknown', 'Error in extraction'], 
                   skills: list[str] | Literal['In Development'], hr_name: str | Literal['Unknown'], hr_link: str | Literal['Unknown'], resume: str, 
                   reposted: bool, date_listed: datetime | Literal['Unknown'], date_applied:  datetime | Literal['Pending'], job_link: str, application_link: str, 
                   questions_list: set | None, connect_request: Literal['In Development']) -> None:
    '''
    Function to create or update the Applied jobs CSV file, once the application is submitted successfully
    '''
    try:
        with open(file_name, mode='a', newline='', encoding='utf-8') as csv_file:
            fieldnames = ['Job ID', 'Title', 'Company', 'Work Location', 'Work Style', 'About Job', 'Experience required', 'Skills required', 'HR Name', 'HR Link', 'Resume', 'Re-posted', 'Date Posted', 'Date Applied', 'Job Link', 'External Job link', 'Questions Found', 'Connect Request']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            if csv_file.tell() == 0: writer.writeheader()
            writer.writerow({'Job ID':truncate_for_csv(job_id), 'Title':truncate_for_csv(title), 'Company':truncate_for_csv(company), 'Work Location':truncate_for_csv(work_location), 'Work Style':truncate_for_csv(work_style), 
                            'About Job':truncate_for_csv(description), 'Experience required': truncate_for_csv(experience_required), 'Skills required':truncate_for_csv(skills), 
                                'HR Name':truncate_for_csv(hr_name), 'HR Link':truncate_for_csv(hr_link), 'Resume':truncate_for_csv(resume), 'Re-posted':truncate_for_csv(reposted), 
                                'Date Posted':truncate_for_csv(date_listed), 'Date Applied':truncate_for_csv(date_applied), 'Job Link':truncate_for_csv(job_link), 
                                'External Job link':truncate_for_csv(application_link), 'Questions Found':truncate_for_csv(questions_list), 'Connect Request':truncate_for_csv(connect_request)})
        csv_file.close()
    except Exception as e:
        print_lg("Failed to update submitted jobs list!", e)
        smart_alert("Failed to update the excel of applied jobs!\nProbably because of 1 of the following reasons:\n1. The file is currently open or in use by another program\n2. Permission denied to write to the file\n3. Failed to find the file", "Failed Logging")



# Function to discard the job application
def discard_job() -> None:
    actions.send_keys(Keys.ESCAPE).perform()
    # Discard may be absent if the modal already closed; avoid noisy logs.
    wait_span_click(driver, 'Discard', 2, silent=True)






# Function to apply to jobs
def run_applications(search_terms: list[str]) -> None:
    applied_jobs = get_applied_job_ids()
    rejected_jobs = set()
    blacklisted_companies = set()
    global current_city, failed_count, skip_count, easy_applied_count, external_jobs_count, tabs_count, pause_before_submit, pause_at_failed_question, useNewResume, dailyEasyApplyLimitReached
    global options, driver, actions, wait, linkedIn_tab
    current_city = current_city.strip()

    if randomize_search_order:  shuffle(search_terms)
    for searchTerm in search_terms:
        # Re-run sticky filter reset for each keyword: LinkedIn can revert
        # per-account sticky toggles on each results-page reload.
        global _sticky_filters_reset_done
        _sticky_filters_reset_done = False
        # Workplace types f_WT=1,2,3; Easy Apply via f_EA=true when easy_apply_only (not f_AL—that is Actively hiring).
        search_url = build_linkedin_jobs_search_url(searchTerm)
        assert_easy_apply_url_contains_f_ea(search_url)
        driver.get(search_url)
        dbg(
            f"Opened job search | easy_apply_only={easy_apply_only} | "
            f"f_EA_in_url={'f_EA=true' in search_url} | url={search_url}"
        )
        try:
            current = driver.current_url
            dbg(f"current_url_after_load={current}")
            if easy_apply_only and "f_EA=true" not in current:
                print_lg(f"[ERROR] LinkedIn stripped f_EA=true from URL after redirect; Easy-Apply filter may not be active: {current}")
        except Exception as url_err:
            dbg(f"Could not read current_url: {url_err}")
        print_lg("\n________________________________________________________________________________________________________________________\n")
        print_lg(f'\n>>>> Now searching for "{searchTerm}" <<<<\n\n')

        apply_filters()

        current_count = 0
        try:
            while current_count < switch_number:
                # Wait until job listings are loaded
                wait.until(EC.presence_of_all_elements_located((By.XPATH, "//li[@data-occludable-job-id]")))

                pagination_element, current_page = get_page_info()

                # Find all job listings in current page
                buffer(3)
                job_listings = driver.find_elements(By.XPATH, "//li[@data-occludable-job-id]")  

            
                for job in job_listings:
                    # if keep_screen_awake: pyautogui.press('shiftright')
                    if current_count >= switch_number: break
                    print_lg("\n-@-\n")

                    job_id,title,company,work_location,work_style,skip = get_job_main_details(job, blacklisted_companies, rejected_jobs)
                    
                    if skip: continue
                    # Redundant fail safe check for applied jobs (non-waiting -> saves ~2s per job)
                    try:
                        already_applied_marker = bool(
                            driver.find_elements(By.CLASS_NAME, "jobs-s-apply__application-link")
                        )
                        if job_id in applied_jobs or already_applied_marker:
                            print_lg(f'Already applied to "{title} | {company}" job. Job ID: {job_id}!')
                            continue
                    except Exception as e:
                        print_lg(f'Trying to Apply to "{title} | {company}" job. Job ID: {job_id}')

                    job_link = "https://www.linkedin.com/jobs/view/"+job_id
                    application_link = "Easy Applied"
                    date_applied = "Pending"
                    hr_link = "Unknown"
                    hr_name = "Unknown"
                    connect_request = "In Development" # Still in development
                    date_listed = "Unknown"
                    skills = "Needs an AI" # Still in development
                    resume = "Pending"
                    reposted = False
                    questions_list = None
                    screenshot_name = "Not Available"

                    jobs_top_card = None
                    try:
                        rejected_jobs, blacklisted_companies, jobs_top_card = check_blacklist(rejected_jobs,job_id,company,blacklisted_companies)
                    except ValueError as e:
                        print_lg(e, 'Skipping this job!\n')
                        failed_job(job_id, job_link, resume, date_listed, "Found Blacklisted words in About Company", e, "Skipped", screenshot_name)
                        skip_count += 1
                        continue
                    except Exception as e:
                        print_lg(f"Failed to scroll to About Company! ({e})")
                        # jobs_top_card stays None; downstream code must handle that



                    # Hiring Manager info
                    try:
                        hr_info_card = WebDriverWait(driver,2).until(EC.presence_of_element_located((By.CLASS_NAME, "hirer-card__hirer-information")))
                        hr_link = hr_info_card.find_element(By.TAG_NAME, "a").get_attribute("href")
                        hr_name = hr_info_card.find_element(By.TAG_NAME, "span").text
                        # if connect_hr:
                        #     driver.switch_to.new_window('tab')
                        #     driver.get(hr_link)
                        #     wait_span_click("More")
                        #     wait_span_click("Connect")
                        #     wait_span_click("Add a note")
                        #     message_box = driver.find_element(By.XPATH, "//textarea")
                        #     message_box.send_keys(connect_request_message)
                        #     if close_tabs: driver.close()
                        #     driver.switch_to.window(linkedIn_tab) 
                        # def message_hr(hr_info_card):
                        #     if not hr_info_card: return False
                        #     hr_info_card.find_element(By.XPATH, ".//span[normalize-space()='Message']").click()
                        #     message_box = driver.find_element(By.XPATH, "//div[@aria-label='Write a message…']")
                        #     message_box.send_keys()
                        #     try_xp(driver, "//button[normalize-space()='Send']")        
                    except Exception as e:
                        print_lg(f'HR info was not given for "{title}" with Job ID: {job_id}!')
                        # print_lg(e)


                    # Calculation of date posted
                    try:
                        # try: time_posted_text = find_by_class(driver, "jobs-unified-top-card__posted-date", 2).text
                        # except: 
                        time_posted_text = jobs_top_card.find_element(By.XPATH, './/span[contains(normalize-space(), " ago")]').text
                        print("Time Posted: " + time_posted_text)
                        if time_posted_text.__contains__("Reposted"):
                            reposted = True
                            time_posted_text = time_posted_text.replace("Reposted", "")
                        date_listed = calculate_date_posted(time_posted_text.strip())
                    except Exception as e:
                        print_lg("Failed to calculate the date posted!",e)


                    description, experience_required, skip, reason, message = get_job_description()
                    
                    # --- Automated Resume Tailoring Hook ---
                    if not skip and use_AI and description != "Unknown" and master_resume_data:
                        print_lg(f"-- Evaluating job relevance for {company} | {title}")
                        relevance = ai_call('check_relevance', aiClient, description, json.dumps(master_resume_data))
                        if isinstance(relevance, dict) and relevance.get("error") == "offline_mode":
                            print_lg("-- OFFLINE MODE: Skipping AI relevance check; applying without filtering.")
                            relevance = {}
                        elif isinstance(relevance, dict) and relevance.get("match_score", 0) >= 85:
                            print_lg(f"---- HIGH MATCH DETECTED ({relevance['match_score']}%)! Generating tailored resume...")
                            tailored_data = ai_call('generate_resume', aiClient, description, json.dumps(master_resume_data))
                            if isinstance(tailored_data, dict) and tailored_data.get("error") == "offline_mode":
                                print_lg("---- OFFLINE MODE: Skipping tailored resume generation.")
                            elif isinstance(tailored_data, dict):
                                # Ensure we save to the root "resume_output" folder
                                root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                                output_dir = os.path.join(root_dir, "resume_output")
                                md_res, tex_res = generate_tailored_files(tailored_data, master_resume_data, output_dir, company, title)
                                print_lg(f"---- Tailored resumes generated: {md_res}, {tex_res}")
                        else:
                            score = relevance.get("match_score", 0) if isinstance(relevance, dict) else 0
                            print_lg(f"-- Match score: {score}% (Reason: {relevance.get('reasoning', 'N/A') if isinstance(relevance, dict) else 'Error'})")
                    # ---------------------------------------

                    if skip:
                        print_lg(message)
                        failed_job(job_id, job_link, resume, date_listed, reason, message, "Skipped", screenshot_name)
                        rejected_jobs.add(job_id)
                        skip_count += 1
                        continue

                    
                    if use_AI and description != "Unknown":
                        try:
                            skills = ai_call('extract_skills', aiClient, description)
                            if isinstance(skills, dict) and skills.get("error") == "offline_mode":
                                skills = "Offline mode - no AI extraction"
                                print_lg("-- OFFLINE MODE: Skipping skill extraction.")
                            else:
                                print_lg(f"Extracted skills using {ai_provider} AI")
                        except Exception as e:
                            print_lg("Failed to extract skills:", e)
                            skills = "Error extracting skills"
                        ##<

                    uploaded = False
                    # Case 1: Easy Apply Button
                    if try_xp(driver, ".//button[@id='jobs-apply-button-id' or (contains(@class,'jobs-apply-button') and contains(@aria-label, 'Easy'))]"):
                        modal = None
                        try: 
                            try:
                                errored = ""
                                modal = get_active_modal()
                                buffer(2)  # Let modal fully render before first interaction
                                try:
                                    dbg(f"Easy Apply modal opened | visible={modal.is_displayed()} | class={modal.get_attribute('class')}")
                                except Exception as dbg_err:
                                    dbg(f"Could not inspect modal: {dbg_err}")
                                # Pass driver (WebDriver), not modal (WebElement); wait_span_click needs driver.execute_script for JS-click fallback
                                if wait_span_click(driver, "Next", 2):
                                    dbg("First Next click succeeded")
                                else:
                                    dbg("First Next click not found - possibly single-page Easy Apply")
                                # if description != "Unknown":
                                #     resume = create_custom_resume(description)
                                resume = "Previous resume"
                                next_button = True
                                questions_list = set()
                                next_counter = 0
                                while next_button:
                                    next_counter += 1
                                    if next_counter >= 15: 
                                        if pause_at_failed_question:
                                            screenshot(driver, job_id, "Needed manual intervention for failed question")
                                            smart_alert("Couldn't answer one or more questions.\nPlease click \"Continue\" once done.\nDO NOT CLICK Back, Next or Review button in LinkedIn.\n\n\n\n\nYou can turn off \"Pause at failed question\" setting in config.py", "Help Needed", "Continue")
                                            next_counter = 1
                                            continue
                                        if questions_list: print_lg("Stuck for one or some of the following questions...", questions_list)
                                        screenshot_name = screenshot(driver, job_id, "Failed at questions")
                                        errored = "stuck"
                                        raise Exception("Seems like stuck in a continuous loop of next, probably because of new questions.")
                                    # Re-locate the modal every iteration: LinkedIn rebuilds
                                    # the Easy Apply DOM between steps, so any reference from
                                    # the previous Next click is stale by the time we touch it.
                                    try:
                                        modal = get_active_modal()
                                    except Exception as mloc_err:
                                        dbg(f"Could not re-locate modal: {mloc_err}")
                                        break
                                    questions_list = fill_easy_apply_form(modal, questions_list, work_location, job_description=description)
                                    if useNewResume and not uploaded: uploaded, resume = upload_resume(modal, default_resume_path)

                                    # Find + click Next/Review/Submit with a bounded retry on
                                    # StaleElementReferenceException. Up to 3 attempts, 1s apart.
                                    click_succeeded = False
                                    intercepted = False
                                    for attempt in range(3):
                                        try:
                                            modal = get_active_modal()
                                            next_button = _find_next_or_review_or_submit(modal)
                                            next_button.click()
                                            click_succeeded = True
                                            break
                                        except StaleElementReferenceException:
                                            dbg(f"Stale element on attempt {attempt+1}/3; re-acquiring modal...")
                                            sleep(1)
                                            continue
                                        except ElementClickInterceptedException:
                                            intercepted = True
                                            break
                                        except NoSuchElementException:
                                            # No more Next/Review/Submit buttons; step complete.
                                            next_button = None
                                            break
                                        except Exception as click_err:
                                            # Fall back to JS click using driver (not modal).
                                            try:
                                                driver.execute_script("arguments[0].click();", next_button)
                                                click_succeeded = True
                                                break
                                            except Exception as js_err:
                                                dbg(f"Next button click failed: {click_err}; JS fallback failed: {js_err}")
                                                next_button = None
                                                break
                                    if intercepted:
                                        break  # About Company photos section or similar overlay.
                                    if not click_succeeded and next_button is None:
                                        # Reached end of form or unrecoverable; exit the while.
                                        break
                                    buffer(click_gap)

                            except NoSuchElementException: errored = "nose"
                            finally:
                                if questions_list and errored != "stuck": 
                                    print_lg("Answered the following questions...", questions_list)
                                    print("\n\n" + "\n".join(str(question) for question in questions_list) + "\n\n")
                                # Optional step: many Easy Apply flows skip Review and go straight to Submit.
                                wait_span_click(driver, "Review", 1, scrollTop=True, silent=True)
                                cur_pause_before_submit = pause_before_submit
                                if errored != "stuck" and cur_pause_before_submit:
                                    if LEARNING_MODE:
                                        print_lg("--- LEARNING MODE: Skipping Submit and Closing Browser ---")
                                        save_questions_to_custom_config(questions_list)
                                        raise Exception("Learning mode: Skipping submission and discarding job.")
                                    decision = smart_confirm('1. Please verify your information.\n2. If you edited something, please return to this final screen.\n3. DO NOT CLICK "Submit Application".\n\n\n\n\nYou can turn off "Pause before submit" setting in config.py\nTo TEMPORARILY disable pausing, click "Disable Pause"', "Confirm your information", ["Disable Pause", "Discard Application", "Submit Application"])
                                    if decision == "Discard Application": raise Exception("Job application discarded by user!")
                                    pause_before_submit = False if "Disable Pause" == decision else True
                                    # try_xp(modal, ".//span[normalize-space(.)='Review']")
                                try:
                                    modal = get_active_modal(5)
                                except Exception:
                                    modal = None
                                follow_company(modal)
                                if _click_submit_easy_apply_final():
                                    date_applied = datetime.now()
                                    if not wait_span_click(driver, "Done", 2, silent=True):
                                        actions.send_keys(Keys.ESCAPE).perform()
                                elif errored != "stuck" and cur_pause_before_submit and "Yes" in smart_confirm("You submitted the application, didn't you 😒?", "Failed to find Submit Application!", ["Yes", "No"]):
                                    date_applied = datetime.now()
                                    wait_span_click(driver, "Done", 2, silent=True)
                                else:
                                    print_lg("Since, Submit Application failed, discarding the job application...")
                                    # if screenshot_name == "Not Available":  screenshot_name = screenshot(driver, job_id, "Failed to click Submit application")
                                    # else:   screenshot_name = [screenshot_name, screenshot(driver, job_id, "Failed to click Submit application")]
                                    if errored == "nose": raise Exception("Failed to click Submit application 😑")


                        except Exception as e:
                            print_lg("Failed to Easy apply!")
                            # print_lg(e)
                            critical_error_log("Somewhere in Easy Apply process",e)
                            failed_job(job_id, job_link, resume, date_listed, "Problem in Easy Applying", e, application_link, screenshot_name)
                            failed_count += 1
                            discard_job()
                            continue
                    else:
                        # Case 2: No Easy Apply button -> skip entirely.
                        # Single-window policy: never open an external apply tab.
                        print_lg(f'Skipping "{title} | {company}" (no Easy Apply button). Job ID: {job_id}')
                        skip_count += 1
                        rejected_jobs.add(job_id)
                        continue

                    submitted_jobs(job_id, title, company, work_location, work_style, description, experience_required, skills, hr_name, hr_link, resume, reposted, date_listed, date_applied, job_link, application_link, questions_list, connect_request)
                    if uploaded:   useNewResume = False

                    print_lg(f'Successfully saved "{title} | {company}" job. Job ID: {job_id} info')
                    current_count += 1
                    if application_link == "Easy Applied": easy_applied_count += 1
                    else:   external_jobs_count += 1
                    applied_jobs.add(job_id)

                    if randomize_wait_times:
                        jitter_time = randint(5, 15)
                        print_lg(f"Jitter enabled. Waiting {jitter_time} seconds before continuing to naturally mimic human behavior...")
                        sleep(jitter_time)
                    
                    if easy_applied_count >= max_applied_jobs:
                        dailyEasyApplyLimitReached = True
                        print_lg(f"\n###############  Configured maximum application limit ({max_applied_jobs}) reached! Safely stopping...  ###############\n")
                        return



                # Switching to next page
                if pagination_element == None:
                    print_lg("Couldn't find pagination element, probably at the end page of results!")
                    break
                try:
                    pagination_element.find_element(By.XPATH, f"//button[@aria-label='Page {current_page+1}']").click()
                    print_lg(f"\n>-> Now on Page {current_page+1} \n")
                except NoSuchElementException:
                    print_lg(f"\n>-> Didn't find Page {current_page+1}. Probably at the end page of results!\n")
                    break

        except (NoSuchWindowException, WebDriverException) as e:
            print_lg(f"Browser window closed or session invalid during '{searchTerm}'. Attempting inline re-init so remaining search_terms can still run...", e)
            try:
                options, driver, actions, wait = _reinit_browser_with_retry()
                driver.get("https://www.linkedin.com/login")
                if not is_logged_in_LN():
                    login_LN()
                linkedIn_tab = driver.current_window_handle
                driver.switch_to.window(linkedIn_tab)
                print_lg(f"Inline re-init succeeded; skipping the rest of '{searchTerm}' and moving to next search term.")
                continue
            except Exception as reinit_err:
                print_lg("Inline re-init failed; bubbling up to main.", reinit_err)
                raise e
        except Exception as e:
            # Check if this happened because we completed the list or an actual error
            if "StaleElementReferenceException" in str(e) or "NoSuchElementException" in str(e):
                print_lg("Encountered stale UI elements or missing job list. Attempting to refresh results...")
                driver.refresh()
                sleep(5)
                continue # Retry current search term
            else:
                print_lg("Failed to find Job listings!")
                critical_error_log("In Applier", e)
                try:
                    # Only print large page source for critical, unknown errors
                    # print_lg(driver.page_source, pretty=True)
                    pass
                except Exception as page_source_error:
                    print_lg(f"Failed to get page source, browser might have crashed. {page_source_error}")
            # print_lg(e)

        
def run(total_runs: int) -> int:
    if dailyEasyApplyLimitReached:
        return total_runs
    print_lg("\n########################################################################################################################\n")
    print_lg(f"Date and Time: {datetime.now()}")
    print_lg(f"Cycle number: {total_runs}")
    print_lg(f"Currently looking for jobs posted within '{date_posted}' and sorting them by '{sort_by}'")
    run_applications(search_terms)
    print_lg("########################################################################################################################\n")
    if not dailyEasyApplyLimitReached:
        print_lg("Sleeping for 5 min...")
        sleep(300)
        print_lg("Few more min... Starting in next 5 min...")
        sleep(300)
    buffer(3)
    return total_runs + 1



chatGPT_tab = False
linkedIn_tab = False

def main() -> None:
    total_runs = 1
    
    # 1. Initialize Browser
    global options, driver, actions, wait
    options, driver, actions, wait = init_browser()

    try:
        global linkedIn_tab, tabs_count, useNewResume, aiClient
        alert_title = "Error Occurred. Closing Browser!"
        validate_config()
        
        if not os.path.exists(default_resume_path):
            smart_alert(text='Your default resume "{}" is missing! Please update it\'s folder path "default_resume_path" in config.py\n\nOR\n\nAdd a resume with exact name and path (check for spelling mistakes including cases).\n\n\nFor now the bot will continue using your previous upload from LinkedIn!'.format(default_resume_path), title="Missing Resume", button="OK")
            useNewResume = False
        
        # Login to LinkedIn
        tabs_count = len(driver.window_handles)
        driver.get("https://www.linkedin.com/login")
        if not is_logged_in_LN(): login_LN()
        
        linkedIn_tab = driver.current_window_handle

        # # Login to ChatGPT in a new tab for resume customization
        # if use_resume_generator:
        #     try:
        #         driver.switch_to.new_window('tab')
        #         driver.get("https://chat.openai.com/")
        #         if not is_logged_in_GPT(): login_GPT()
        #         open_resume_chat()
        #         global chatGPT_tab
        #         chatGPT_tab = driver.current_window_handle
        #     except Exception as e:
        #         print_lg("Opening OpenAI chatGPT tab failed!")
        if use_AI:
            aiClient = None # Handled by ai_call failover

            try:
                about_company_for_ai = " ".join([word for word in (first_name+" "+last_name).split() if len(word) > 3])
                print_lg(f"Extracted about company info for AI: '{about_company_for_ai}'")
            except Exception as e:
                print_lg("Failed to extract about company info!", e)
        
        # Start applying to jobs
        driver.switch_to.window(linkedIn_tab)
        total_runs = run(total_runs)
        while(run_non_stop):
            if cycle_date_posted:
                date_options = ["Any time", "Past month", "Past week", "Past 24 hours"]
                global date_posted
                
                # Standardize current date_posted to a valid option
                if date_posted not in date_options:
                    date_posted = "Any time"
                
                current_idx = date_options.index(date_posted)
                next_idx = (current_idx + 1) % len(date_options)
                
                # If we want to stop at 24h instead of looping
                if stop_date_cycle_at_24hr and current_idx == len(date_options) - 1:
                    next_idx = current_idx
                
                date_posted = date_options[next_idx]
            if alternate_sortby:
                global sort_by
                sort_by = "Most recent" if sort_by == "Most relevant" else "Most relevant"
                total_runs = run(total_runs)
                sort_by = "Most recent" if sort_by == "Most relevant" else "Most relevant"
            total_runs = run(total_runs)
            if dailyEasyApplyLimitReached:
                break
        

    except (NoSuchWindowException, InvalidSessionIdException, WebDriverException) as e:
        print_lg("Browser window closed or session is invalid. Attempting one re-init...", e)
        try:
            options, driver, actions, wait = _reinit_browser_with_retry()
            driver.get("https://www.linkedin.com/login")
            if not is_logged_in_LN():
                login_LN()
            linkedIn_tab = driver.current_window_handle
            driver.switch_to.window(linkedIn_tab)
            total_runs = run(total_runs)
        except Exception as e2:
            print_lg("Re-init failed. Exiting.", e2)
    except Exception as e:
        critical_error_log("In Applier Main", e)
        smart_alert(e,alert_title)
    finally:
        summary = "Total runs: {}\nJobs Easy Applied: {}\nExternal job links collected: {}\nTotal applied or collected: {}\nFailed jobs: {}\nIrrelevant jobs skipped: {}\n".format(total_runs,easy_applied_count,external_jobs_count,easy_applied_count + external_jobs_count,failed_count,skip_count)
        print_lg(summary)
        print_lg("\n\nTotal runs:                     {}".format(total_runs))
        print_lg("Jobs Easy Applied:              {}".format(easy_applied_count))
        print_lg("External job links collected:   {}".format(external_jobs_count))
        print_lg("                              ----------")
        print_lg("Total applied or collected:     {}".format(easy_applied_count + external_jobs_count))
        print_lg("\nFailed jobs:                    {}".format(failed_count))
        print_lg("Irrelevant jobs skipped:        {}\n".format(skip_count))
        if randomly_answered_questions: print_lg("\n\nQuestions randomly answered:\n  {}  \n\n".format(";\n".join(str(question) for question in randomly_answered_questions)))
        
        msg = f"Summary:\n{summary}"
        smart_alert(msg, "Exiting..")
        print_lg(msg,"Closing the browser...")
        if tabs_count >= 10:
            msg = "NOTE: IF YOU HAVE MORE THAN 10 TABS OPENED, PLEASE CLOSE OR BOOKMARK THEM!\n\nOr it's highly likely that application will just open browser and not do anything next time!" 
            smart_alert(msg,"Info")
            print_lg("\n"+msg)
        ##> ------ Yang Li : MARKYangL - Feature ------
        if use_AI:
            # Multi-provider cleanup is handled internally by dispatcher if needed
            print_lg("Closing AI sessions...")
        ##<
        try:
            if driver:
                driver.quit()
        except WebDriverException as e:
            print_lg("Browser already closed.", e)
        except Exception as e: 
            critical_error_log("When quitting...", e)


if __name__ == "__main__":
    main()
