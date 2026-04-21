import os
import sys
from applybot.helpers import make_directories
from config.settings import (
    run_in_background,
    stealth_mode,
    disable_extensions,
    safe_mode,
    file_name,
    failed_file_name,
    logs_folder_path,
    generated_resume_path,
    use_chromium,
    chromium_binary_path,
)
from config.questions import default_resume_path
if stealth_mode:
    import undetected_chromedriver as uc
else: 
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    # from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from applybot.helpers import (
    find_default_profile_directory,
    critical_error_log,
    print_lg,
    get_chrome_major_version,
    smart_alert,
    get_chromium_temp_profile,
    find_chromium_user_data_directory,
    get_default_temp_profile,
    resolve_chromium_binary_path,
)
from selenium.common.exceptions import SessionNotCreatedException
import psutil

def is_user_browser_holding_default_profile() -> bool:
    """
    Returns True if a user-launched Chrome or Chromium is already using the default
    profile (cannot be opened twice by automation). Caller should warn or close the browser.
    """
    from config.settings import use_chromium as use_cr

    if use_cr:
        profile_marker = "Application Support/Chromium"
    else:
        profile_marker = "Application Support/Google/Chrome"

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            name = (proc.info.get('name') or '').lower()
            if use_cr:
                if 'chromium' not in name:
                    continue
            else:
                if 'google chrome' not in name and name != 'chrome':
                    continue
            cmdline = " ".join(proc.info.get('cmdline') or [])
            if '--headless' in cmdline:
                continue
            # Ignore Chrome instances launched against the bot's isolated profile
            # (they are ours, or a leftover we'll clean up).
            if 'auto-job-apply-profile' in cmdline or 'chromium-auto-job' in cmdline:
                continue
            # Ignore Chrome helper/renderer/utility subprocesses (they don't carry user profile flags).
            if '--type=' in cmdline or 'Helper' in (proc.info.get('name') or ''):
                continue
            # Helper / GPU processes often omit --user-data-dir; do not treat that as "default profile in use".
            if '--user-data-dir' not in cmdline:
                continue
            # A real browser process with some other profile dir may still conflict on macOS; keep a narrow check.
            if sys.platform == "darwin" and profile_marker in cmdline:
                if 'auto-job-apply-profile' not in cmdline and 'chromium-auto-job' not in cmdline:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False


def cleanup_zombie_processes():
    """
    Search for and terminate orphaned chromedriver or undetected_chromedriver 
    processes to prevent dock clutter and profile locks.
    """
    print_lg("Cleaning up any leftover browser processes...")
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Look for chromedriver or undetected_chromedriver
            name = proc.info['name'].lower()
            cmdline = " ".join(proc.info['cmdline'] or [])
            
            if 'chromedriver' in name or 'undetected' in name:
                # Don't kill ourselves or our immediate children if we were careful
                if proc.info['pid'] != current_pid:
                    print_lg(f"Terminating zombie driver process: {proc.info['pid']} ({name})")
                    proc.terminate()
            
            # Kill any Chrome/Chromium (headless or not) that is holding the bot's isolated profile
            # (e.g. leftover warm-up window or crashed previous run) — it would block attach.
            if ('chrome' in name or 'chromium' in name) and (
                'auto-job-apply-profile' in cmdline or 'chromium-auto-job' in cmdline
            ):
                 print_lg(f"Terminating leftover Chrome on bot profile: {proc.info['pid']}")
                 proc.terminate()

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Clear stale Singleton lock files in the bot profile dir — they block Chrome from launching
    try:
        import pathlib
        for prof in (get_default_temp_profile(), get_chromium_temp_profile()):
            pdir = pathlib.Path(prof)
            if not pdir.exists():
                continue
            for marker in ("SingletonCookie", "SingletonLock", "SingletonSocket", "RunningChromeVersion"):
                f = pdir / marker
                try:
                    if f.exists() or f.is_symlink():
                        f.unlink()
                except Exception:
                    pass
    except Exception:
        pass

def createChromeSession(isRetry: bool = False):
    make_directories([file_name,failed_file_name,logs_folder_path+"/screenshots",default_resume_path,generated_resume_path+"/temp"])
    # Set up WebDriver with Chrome Profile
    options = uc.ChromeOptions() if stealth_mode else Options()

    if use_chromium:
        chromium_bin = resolve_chromium_binary_path((chromium_binary_path or "").strip())
        if not chromium_bin:
            msg = (
                "use_chromium is True but Chromium was not found. Install on macOS with:\n"
                "  brew install --cask chromium\n"
                "Or set chromium_binary_path in config/settings.py to the full path of the Chromium binary."
            )
            print_lg(msg)
            smart_alert(msg, "Chromium not found")
            exit()
        options.binary_location = chromium_bin
        print_lg(f"Using Chromium binary: {chromium_bin}")

    if run_in_background:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
    if disable_extensions:  options.add_argument("--disable-extensions")

    print_lg("IF YOU HAVE MORE THAN 10 TABS OPENED, PLEASE CLOSE OR BOOKMARK THEM! Or it's highly likely that application will just open browser and not do anything!")
    
    # 0. Check for existing browser connection
    from config.settings import use_existing_browser, debugger_port
    if use_existing_browser:
        print_lg(f"Attempting to attach to existing browser on port {debugger_port}...")
        options = Options() if not stealth_mode else uc.ChromeOptions()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debugger_port}")
        try:
            # When attaching, we usually use standard Chrome to avoid UC initialization conflicts
            driver = webdriver.Chrome(options=options)
            print_lg("Successfully attached to existing browser!")
            wait = WebDriverWait(driver, 5)
            actions = ActionChains(driver)
            return options, driver, actions, wait
        except Exception as e:
            print_lg(f"Failed to attach to existing browser: {e}. Falling back to new session.")
    
    # 1. Cleanup old processes before starting a fresh one
    cleanup_zombie_processes()

    # 1b. Warn if a user Chrome is already holding the default profile.
    # (macOS only; the persistent profile directory cannot be loaded twice.)
    if not safe_mode and is_user_browser_holding_default_profile():
        browser_name = "Chromium" if use_chromium else "Google Chrome"
        print_lg(
            f"WARNING: {browser_name} is already running with your default profile. "
            "The persistent profile cannot be attached twice — the bot will fall back "
            f"to a guest profile. Close {browser_name} fully (Cmd+Q) before running, or set "
            "safe_mode=True to suppress this warning."
        )

    chrome_profile_dir = find_default_profile_directory()
    chromium_profile_dir = find_chromium_user_data_directory()

    if isRetry:
        print_lg("Will login with a guest profile, browsing history will not be saved in the browser!")
        guest_dir = get_chromium_temp_profile() if use_chromium else get_default_temp_profile()
        options.add_argument(f"--user-data-dir={guest_dir}")
    elif not safe_mode:
        if use_chromium and chromium_profile_dir:
            options.add_argument(f"--user-data-dir={chromium_profile_dir}")
        elif not use_chromium and chrome_profile_dir:
            options.add_argument(f"--user-data-dir={chrome_profile_dir}")
        else:
            print_lg("Logging in with a guest profile, Web history will not be saved!")
            guest_dir = get_chromium_temp_profile() if use_chromium else get_default_temp_profile()
            options.add_argument(f"--user-data-dir={guest_dir}")
    else:
        print_lg("Logging in with a guest profile, Web history will not be saved!")
        guest_dir = get_chromium_temp_profile() if use_chromium else get_default_temp_profile()
        options.add_argument(f"--user-data-dir={guest_dir}")
    if stealth_mode:
        # try: 
        #     driver = uc.Chrome(driver_executable_path="C:\\Program Files\\Google\\Chrome\\chromedriver-win64\\chromedriver.exe", options=options)
        # except (FileNotFoundError, PermissionError) as e: 
        #     print_lg("(Undetected Mode) Got '{}' when using pre-installed ChromeDriver.".format(type(e).__name__)) 
            print_lg("Downloading Chrome Driver... This may take some time. Undetected mode requires download every run!")
            detected_version = get_chrome_major_version()
            if detected_version:
                print_lg(f"Detected Chrome version: {detected_version}. Forcing ChromeDriver version match...")
                driver = uc.Chrome(options=options, version_main=detected_version)
            else:
                driver = uc.Chrome(options=options)
    else: driver = webdriver.Chrome(options=options) #, service=Service(executable_path="C:\\Program Files\\Google\\Chrome\\chromedriver-win64\\chromedriver.exe"))
    driver.maximize_window()
    wait = WebDriverWait(driver, 5)
    actions = ActionChains(driver)
    return options, driver, actions, wait

def init_browser():
    """
    Explicit entry point for browser initialization to avoid global import side-effects.
    """
    try:
        return createChromeSession()
    except SessionNotCreatedException as e:
        critical_error_log("Failed to create Chrome Session, retrying with guest profile", e)
        return createChromeSession(True)
    except Exception as e:
        msg = 'Seems like Google Chrome is out dated. Update browser and try again! \n\n\nIf issue persists, try Safe Mode. Set, safe_mode = True in config.py \n\nPlease check the project README for solutions.'
        if isinstance(e, TimeoutError): msg = "Couldn't download Chrome-driver. Set stealth_mode = False in config!"
        print_lg(msg)
        critical_error_log("In Opening Chrome", e)
        smart_alert(msg, "Error in opening chrome")
        exit()
    
