###################################################### CONFIGURE YOUR TOOLS HERE ######################################################


# >>>>>>>>>>> Global Settings <<<<<<<<<<<

# Directory and name of the files where history of applied jobs is saved (Sentence after the last "/" will be considered as the file name).
file_name = "history/applications.csv"
failed_file_name = "history/failures.csv"
logs_folder_path = "logs/"
generated_resume_path = "all resumes/"

# Set the maximum amount of time allowed to wait between each click in secs
click_gap = 2                      # Enter max allowed secs to wait approximately. (Only Non Negative Integers Eg: 0,1,2,3,....)

# If you want to see Chrome running then set run_in_background as False (May reduce performance). 
run_in_background = False          # True or False, Note: True or False are case-sensitive ,   If True, this will make pause_at_failed_question, pause_before_submit and run_in_background as False

# Should the tool pause before every submit application during easy apply to let you check the information?
pause_before_submit = False         # True or False, Note: True or False are case-sensitive

# If you want to disable extensions then set disable_extensions as True (Better for performance)
disable_extensions = True          # True or False, Note: True or False are case-sensitive

# Run in safe mode. Set this true if chrome is taking too long to open or if you have multiple profiles in browser. This will open chrome in guest profile!
safe_mode = False                  # True or False, Note: True or False are case-sensitive

# Do you want scrolling to be smooth or instantaneous? (Can reduce performance if True)
smooth_scroll = False              # True or False, Note: True or False are case-sensitive

# If enabled (True), the program would keep your screen active and prevent PC from sleeping. Instead you could disable this feature (set it to false) and adjust your PC sleep settings to Never Sleep or a preferred time. 
keep_screen_awake = True           # True or False, Note: True or False are case-sensitive (Note: Will temporarily deactivate when any application dialog boxes are present (Eg: Pause before submit, Help needed for a question..))

# Run in undetected mode to bypass anti-bot protections (Preview Feature, UNSTABLE. Recommended to leave it as False)
stealth_mode = False             # True or False, Note: True or False are case-sensitive

# Skip LinkedIn's filter UI and rely purely on URL query params (recommended, resilient to LinkedIn A/B layout changes).
# When True, the bot does NOT open the "All filters" panel; all filters (Easy Apply, workplace, sort, date, job type,
# experience level) are applied via the search URL directly in build_linkedin_jobs_search_url.
use_url_filters_only = True        # True or False, Note: True or False are case-sensitive

# Launch Chromium instead of Google Chrome (recommended for isolated testing). macOS: brew install --cask chromium
use_chromium = False               # True or False, Note: True or False are case-sensitive
# Full path to the Chromium binary; leave "" to auto-detect (e.g. /Applications/Chromium.app/Contents/MacOS/Chromium).
chromium_binary_path = ""          # Example: "/Applications/Chromium.app/Contents/MacOS/Chromium"

# Legacy setting: Easy Apply always leaves LinkedIn's "Follow … stay up to date" box
# unchecked regardless of this flag (automation policy). Kept for config compatibility.
follow_companies = False           # True or False, Note: True or False are case-sensitive

max_applied_jobs = 3               # Maximum Easy Apply submissions per run (see logs/ and logs/screenshots/)
randomize_wait_times = True        # Enable human-like randomized delays between actions

# Pause after search for manual review
pause_after_filters = False          # Set to True if you want to verify results before bot starts applying

# >>>>>>>>>>> Browser Reuse Settings <<<<<<<<<<<
# If you have so many Chrome instances, keep this False to let the bot manage and cleanup its own windows.
# If you want to use your OWN already-opened browser (with your LinkedIn logged in), set this to True.
# NOTE: To use an existing browser, you MUST first launch Chrome with: 
# /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
use_existing_browser = False       
debugger_port = 9222                


# Do you want to see AI-related error alerts?
showAiErrorAlerts = True           # True or False

############################################################################################################