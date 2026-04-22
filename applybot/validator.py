from __future__ import annotations
# from config.XdepricatedX import *

__validation_file_path = ""

def check_int(var: int, var_name: str, min_value: int=0) -> bool | TypeError | ValueError:
    if not isinstance(var, int): raise TypeError(f'The variable "{var_name}" in "{__validation_file_path}" must be an Integer!\nReceived "{var}" of type "{type(var)}" instead!\n\nSolution:\nPlease open "{__validation_file_path}" and update "{var_name}" to be an Integer.\nExample: `{var_name} = 10`\n\nNOTE: Do NOT surround Integer values in quotes ("10")X !\n\n')
    if var < min_value: raise ValueError(f'The variable "{var_name}" in "{__validation_file_path}" expects an Integer greater than or equal to `{min_value}`! Received `{var}` instead!\n\nSolution:\nPlease open "{__validation_file_path}" and update "{var_name}" accordingly.')
    return True

def check_boolean(var: bool, var_name: str) -> bool | ValueError:
    if isinstance(var, bool):
        return True
    raise ValueError(f'The variable "{var_name}" in "{__validation_file_path}" expects a Boolean input `True` or `False`, not "{var}" of type "{type(var)}" instead!\n\nSolution:\nPlease open "{__validation_file_path}" and update "{var_name}" to either `True` or `False` (case-sensitive, T and F must be CAPITAL/uppercase).\nExample: `{var_name} = True`\n\nNOTE: Do NOT surround Boolean values in quotes ("True")X !\n\n')

def check_string(var: str, var_name: str, options: list=[], min_length: int=0) -> bool | TypeError | ValueError:
    if not isinstance(var, str): raise TypeError(f'Invalid input for {var_name}. Expecting a String!')
    if min_length > 0 and len(var) < min_length: raise ValueError(f'Invalid input for {var_name}. Expecting a String of length at least {min_length}!')
    if len(options) > 0 and var not in options: raise ValueError(f'Invalid input for {var_name}. Expecting a value from {options}, not {var}!')
    return True

def check_list(var: list, var_name: str, options: list=[], min_length: int=0) -> bool | TypeError | ValueError:
    if not isinstance(var, list): 
        raise TypeError(f'Invalid input for {var_name}. Expecting a List!')
    if len(var) < min_length: raise ValueError(f'Invalid input for {var_name}. Expecting a List of length at least {min_length}!')
    for element in var:
        if not isinstance(element, str): raise TypeError(f'Invalid input for {var_name}. All elements in the list must be strings!')
        if len(options) > 0 and element not in options: raise ValueError(f'Invalid input for {var_name}. Expecting all elements to be values from {options}. This "{element}" is NOT in options!')
    return True



def validate_personals() -> None | ValueError | TypeError:
    '''
    Validates all variables in the `/config/personals.py` file.
    '''
    global __validation_file_path
    __validation_file_path = "config/personals.py"
    from config import personals as p

    check_string(p.first_name, "first_name", min_length=1)
    check_string(p.middle_name, "middle_name")
    check_string(p.last_name, "last_name", min_length=1)

    check_string(p.phone_number, "phone_number", min_length=10)

    check_string(p.current_city, "current_city")

    check_string(p.street, "street")
    check_string(p.state, "state")
    check_string(p.zipcode, "zipcode")
    check_string(p.country, "country")

    check_string(p.ethnicity, "ethnicity", ["Decline", "Hispanic/Latino", "American Indian or Alaska Native", "Asian", "Black or African American", "Native Hawaiian or Other Pacific Islander", "White", "Other"],  min_length=0)
    check_string(p.gender, "gender", ["Male", "Female", "Other", "Decline", ""])
    check_string(p.disability_status, "disability_status", ["Yes", "No", "Decline"])
    check_string(p.veteran_status, "veteran_status", ["Yes", "No", "Decline"])


def validate_questions() -> None | ValueError | TypeError:
    '''
    Validates all variables in the `/config/questions.py` file.
    '''
    global __validation_file_path
    __validation_file_path = "config/questions.py"
    from config import questions as q

    check_string(q.default_resume_path, "default_resume_path")
    check_string(q.years_of_experience, "years_of_experience")
    check_string(q.require_visa, "require_visa", ["Yes", "No"])
    check_string(q.website, "website")
    check_string(q.linkedIn, "linkedIn")
    check_int(q.desired_salary, "desired_salary")
    check_string(q.us_citizenship, "us_citizenship", ["U.S. Citizen/Permanent Resident", "Non-citizen allowed to work for any employer", "Non-citizen allowed to work for current employer", "Non-citizen seeking work authorization", "Canadian Citizen/Permanent Resident", "Other"])
    check_string(q.linkedin_headline, "linkedin_headline")
    check_int(q.notice_period, "notice_period")
    check_int(q.current_ctc, "current_ctc")
    check_string(q.linkedin_summary, "linkedin_summary")
    check_string(q.cover_letter, "cover_letter")
    check_string(q.recent_employer, "recent_employer")
    check_string(q.confidence_level, "confidence_level")

    check_boolean(q.pause_before_submit, "pause_before_submit")
    check_boolean(q.pause_at_failed_question, "pause_at_failed_question")
    check_boolean(q.overwrite_previous_answers, "overwrite_previous_answers")


def validate_search() -> None | ValueError | TypeError:
    '''
    Validates all variables in the `/config/search.py` file.
    '''
    global __validation_file_path
    __validation_file_path = "config/search.py"
    from config import search as s

    check_list(s.search_terms, "search_terms", min_length=1)
    check_string(s.search_location, "search_location")
    check_int(s.switch_number, "switch_number", 1)
    check_boolean(s.randomize_search_order, "randomize_search_order")

    check_string(s.sort_by, "sort_by", ["", "Most recent", "Most relevant"])
    check_string(s.date_posted, "date_posted", ["", "Any time", "Past month", "Past week", "Past 24 hours"])
    check_string(s.salary, "salary")

    check_boolean(s.easy_apply_only, "easy_apply_only")

    check_list(s.experience_level, "experience_level", ["Internship", "Entry level", "Associate", "Mid-Senior level", "Director", "Executive"])
    check_list(s.job_type, "job_type", ["Full-time", "Part-time", "Contract", "Temporary", "Volunteer", "Internship", "Other"])
    check_list(s.on_site, "on_site", ["On-site", "Remote", "Hybrid"])

    check_list(s.companies, "companies")
    check_list(s.location, "location")
    check_list(s.industry, "industry")
    check_list(s.job_function, "job_function")
    check_list(s.job_titles, "job_titles")
    check_list(s.benefits, "benefits")
    check_list(s.commitments, "commitments")

    check_boolean(s.under_10_applicants, "under_10_applicants")
    check_boolean(s.in_your_network, "in_your_network")
    check_boolean(s.fair_chance_employer, "fair_chance_employer")

    check_list(s.about_company_bad_words, "about_company_bad_words")
    check_list(s.about_company_good_words, "about_company_good_words")
    check_list(s.bad_words, "bad_words")
    check_boolean(s.security_clearance, "security_clearance")
    check_boolean(s.did_masters, "did_masters")
    check_int(s.current_experience, "current_experience", -1)
    check_int(s.min_experience, "min_experience", 0)

    check_boolean(s.close_tabs, "close_tabs")
    check_boolean(s.run_non_stop, "run_non_stop")
    check_boolean(s.alternate_sortby, "alternate_sortby")
    check_boolean(s.cycle_date_posted, "cycle_date_posted")
    check_boolean(s.stop_date_cycle_at_24hr, "stop_date_cycle_at_24hr")




def validate_secrets() -> None | ValueError | TypeError:
    '''
    Validates all variables in the `/config/secrets.py` file.

    When ``use_AI`` is False, LLM URL/key/model/provider checks are skipped so
    ``--validate-config`` can pass without API keys (offline / no-AI runs).
    '''
    global __validation_file_path
    __validation_file_path = "config/secrets.py"
    from config import secrets as sec

    check_string(sec.username, "username", min_length=5)
    check_string(sec.password, "password", min_length=5)

    check_boolean(sec.use_AI, "use_AI")
    check_boolean(sec.stream_output, "stream_output")
    if sec.use_AI:
        check_string(sec.llm_api_url, "llm_api_url", min_length=5)
        check_string(sec.llm_api_key, "llm_api_key")
        check_string(sec.ai_provider, "ai_provider", ["openai", "gemini"])
        check_string(sec.llm_model, "llm_model")


def validate_settings() -> None | ValueError | TypeError:
    '''
    Validates all variables in the `/config/settings.py` file.
    '''
    global __validation_file_path
    __validation_file_path = "config/settings.py"
    from config import settings as st

    check_boolean(st.follow_companies, "follow_companies")
    # check_boolean(connect_hr, "connect_hr")
    # check_string(connect_request_message, "connect_request_message", min_length=10)

    # check_string(generated_resume_path, "generated_resume_path", min_length=1)

    check_boolean(st.pause_after_filters, "pause_after_filters")
    check_boolean(st.use_url_filters_only, "use_url_filters_only")
    check_boolean(st.use_existing_browser, "use_existing_browser")
    check_int(st.debugger_port, "debugger_port", 1)
    if st.debugger_port > 65535:
        raise ValueError(
            f'The variable "debugger_port" in "{__validation_file_path}" must be <= 65535! Received `{st.debugger_port}`.'
        )
    check_boolean(st.showAiErrorAlerts, "showAiErrorAlerts")

    check_string(st.file_name, "file_name", min_length=1)
    check_string(st.failed_file_name, "failed_file_name", min_length=1)
    check_string(st.logs_folder_path, "logs_folder_path", min_length=1)

    check_int(st.click_gap, "click_gap", 0)
    check_int(st.max_applied_jobs, "max_applied_jobs", 1)
    check_boolean(st.randomize_wait_times, "randomize_wait_times")

    check_boolean(st.run_in_background, "run_in_background")
    check_boolean(st.disable_extensions, "disable_extensions")
    check_boolean(st.safe_mode, "safe_mode")
    check_boolean(st.smooth_scroll, "smooth_scroll")
    check_boolean(st.keep_screen_awake, "keep_screen_awake")
    check_boolean(st.stealth_mode, "stealth_mode")
    check_boolean(st.use_chromium, "use_chromium")
    check_string(st.chromium_binary_path, "chromium_binary_path")




def validate_config() -> bool | ValueError | TypeError:
    '''
    Runs all validation functions to validate all variables in the config files.
    '''
    validate_personals()
    validate_questions()
    validate_search()
    validate_secrets()
    validate_settings()

    # validate_String(chatGPT_username, "chatGPT_username")
    # validate_String(chatGPT_password, "chatGPT_password")
    # validate_String(chatGPT_resume_chat_title, "chatGPT_resume_chat_title")
    return True

