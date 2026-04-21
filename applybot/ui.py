from __future__ import annotations
# Modules

import sys

from config.settings import click_gap, smooth_scroll
from applybot.helpers import buffer, print_lg, sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains

# Click Functions
def wait_span_click(driver: WebDriver, text: str, time: float=5.0, click: bool=True, scroll: bool=True, scrollTop: bool=False, silent: bool = False) -> WebElement | bool:
    '''
    Finds the span element with the given `text`.
    - Returns `WebElement` if found, else `False` if not found.
    - Clicks on it if `click = True`.
    - Will spend a max of `time` seconds in searching for each element.
    - Will scroll to the element if `scroll = True`.
    - Will scroll to the top if `scrollTop = True`.
    - If `silent` is True, missing elements are not logged (for optional UI steps).
    '''
    if text:
        fallback_xpaths = [
            f'.//span[contains(normalize-space(.), "{text}")]',
            f'.//button[contains(normalize-space(.), "{text}")]',
            f'.//button[contains(@aria-label, "{text}")]',
            f'.//button[.//span[contains(normalize-space(.), "{text}")]]',
        ]
        button = None
        last_exc = None
        for xp in fallback_xpaths:
            try:
                button = WebDriverWait(driver, time).until(EC.presence_of_element_located((By.XPATH, xp)))
                if button:
                    break
            except Exception as e:
                last_exc = e
                continue
        if not button:
            if not silent:
                print_lg("Click Failed! Didn't find '" + text + "'")
            return False

        if scroll:  scroll_to_view(driver, button, scrollTop)
        if click:
            try:
                button.click()
            except Exception:
                try:
                    driver.execute_script("arguments[0].click();", button)
                except Exception as e:
                    print_lg(f"Click via JS fallback failed for '{text}': {e}")
                    return False
            buffer(click_gap)
        return button

def multi_sel(driver: WebDriver, texts: list, time: float=5.0) -> None:
    '''
    - For each text in the `texts`, tries to find and click `span` element with that text.
    - Will spend a max of `time` seconds in searching for each element.
    '''
    for text in texts:
        ##> ------ Dheeraj Deshwal : dheeraj20194@iiitd.ac.in/dheerajdeshwal9811@gmail.com - Bug fix ------
        wait_span_click(driver, text, time, False)
        ##<
        try:
            button = WebDriverWait(driver,time).until(EC.presence_of_element_located((By.XPATH, './/span[contains(normalize-space(.), "'+text+'")]')))
        except Exception:
            try:
                button = WebDriverWait(driver,time).until(EC.presence_of_element_located((By.XPATH, './/button[contains(normalize-space(.), "'+text+'")]')))
            except Exception:
                print_lg("Click Failed! Didn't find '"+text+"'")
                continue

        scroll_to_view(driver, button)
        button.click()
        buffer(click_gap)

def multi_sel_noWait(driver: WebDriver, texts: list, actions: ActionChains = None) -> None:
    '''
    - For each text in the `texts`, tries to find and click `span` element with that class.
    - If `actions` is provided, bot tries to search and Add the `text` to this filters list section.
    - Won't wait to search for each element, assumes that element is rendered.
    '''
    for text in texts:
        try:
            try:
                button = driver.find_element(By.XPATH, './/span[contains(normalize-space(.), "'+text+'")]')
            except Exception:
                button = driver.find_element(By.XPATH, './/button[contains(normalize-space(.), "'+text+'")]')
            scroll_to_view(driver, button)
            button.click()
            buffer(click_gap)
        except Exception as e:
            if actions: company_search_click(driver,actions,text)
            else:   
                print_lg("Click Failed! Didn't find '"+text+"'")
                # print_lg(e)

def toggle_switch(
    driver: WebDriver,
    actions: ActionChains,
    text: str,
    desired_on: bool = True,
) -> None:
    '''
    State-aware toggle for LinkedIn's <input role="switch"> filter toggles
    (Easy Apply, Under 10 applicants, In your network, Fair Chance Employer...).

    Reads the toggle's `aria-checked` attribute and only clicks if the current
    state differs from `desired_on`. Prevents the classic bug where a blind
    click UNDOES an already-correct URL-level filter (e.g. `f_EA=true` arrives
    with Easy Apply ON, a blind click turns it OFF).

    - `desired_on=True`  -> ensure the toggle ends up ON (default, backward-compat).
    - `desired_on=False` -> ensure the toggle ends up OFF.
    '''
    try:
        list_container = driver.find_element(
            By.XPATH, './/h3[normalize-space()="' + text + '"]/ancestor::fieldset'
        )
        button = list_container.find_element(By.XPATH, './/input[@role="switch"]')
        current_on = (button.get_attribute("aria-checked") or "").lower() == "true"
        if current_on == desired_on:
            # Already in desired state; do not click.
            return
        scroll_to_view(driver, button)
        actions.move_to_element(button).click().perform()
        buffer(click_gap)
    except Exception:
        print_lg("Click Failed! Didn't find '" + text + "'")

# Find functions
def find_by_class(driver: WebDriver, class_name: str, time: float=5.0) -> WebElement | Exception:
    '''
    Waits for a max of `time` seconds for element to be found, and returns `WebElement` if found, else `Exception` if not found.
    '''
    return WebDriverWait(driver, time).until(EC.presence_of_element_located((By.CLASS_NAME, class_name)))

# Scroll functions
def scroll_to_view(driver: WebDriver, element: WebElement, top: bool = False, smooth_scroll: bool = smooth_scroll) -> None:
    '''
    Scrolls the `element` to view.
    - `smooth_scroll` will scroll with smooth behavior.
    - `top` will scroll to the `element` to top of the view.
    '''
    if top:
        return driver.execute_script('arguments[0].scrollIntoView();', element)
    behavior = "smooth" if smooth_scroll else "instant"
    return driver.execute_script('arguments[0].scrollIntoView({block: "center", behavior: "'+behavior+'" });', element)

# Enter input text functions
def text_input_by_ID(driver: WebDriver, id: str, value: str, time: float=5.0) -> None | Exception:
    '''
    Enters `value` into the input field with the given `id` if found, else throws NotFoundException.
    - `time` is the max time to wait for the element to be found.
    '''
    username_field = WebDriverWait(driver, time).until(EC.presence_of_element_located((By.ID, id)))
    select_all = Keys.COMMAND + "a" if sys.platform == "darwin" else Keys.CONTROL + "a"
    username_field.send_keys(select_all)
    username_field.send_keys(value)

def try_xp(driver: WebDriver, xpath: str, click: bool=True) -> WebElement | bool:
    try:
        if click:
            driver.find_element(By.XPATH, xpath).click()
            return True
        else:
            return driver.find_element(By.XPATH, xpath)
    except Exception:
        return False

def try_linkText(driver: WebDriver, linkText: str) -> WebElement | bool:
    try:
        return driver.find_element(By.LINK_TEXT, linkText)
    except Exception:
        return False

def try_find_by_classes(driver: WebDriver, classes: list[str]) -> WebElement | None:
    for cla in classes:
        try:
            return driver.find_element(By.CLASS_NAME, cla)
        except Exception:
            pass
    return None

def company_search_click(driver: WebDriver, actions: ActionChains, companyName: str) -> None:
    '''
    Tries to search and Add the company to company filters list.
    '''
    wait_span_click(driver,"Add a company",1)
    search = driver.find_element(By.XPATH,"(.//input[@placeholder='Add a company'])[1]")
    select_all = Keys.COMMAND + "a" if sys.platform == "darwin" else Keys.CONTROL + "a"
    search.send_keys(select_all)
    search.send_keys(companyName)
    buffer(3)
    actions.send_keys(Keys.DOWN).perform()
    actions.send_keys(Keys.ENTER).perform()
    print_lg(f'Tried searching and adding "{companyName}"')

def text_input(actions: ActionChains, textInputEle: WebElement | bool, value: str, textFieldName: str = "Text") -> None | Exception:
    if textInputEle:
        sleep(1)
        # actions.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
        textInputEle.clear()
        textInputEle.send_keys(value.strip())
        sleep(2)
        actions.send_keys(Keys.ENTER).perform()
    else:
        print_lg(f'{textFieldName} input was not given!')
def handle_interruptModals(driver: WebDriver) -> bool:
    '''
    Identifies and clears common LinkedIn interrupt modals like 'Save this application?'.
    - Clicks 'Discard' if the save dialog appears.
    - Returns True if an interruption was handled.
    '''
    interrupted = False
    # Check for 'Save this application?' dialog
    try:
        # Looking for a modal that contains 'Save' or 'Discard'
        save_dialog = driver.find_elements(By.XPATH, '//*[contains(normalize-space(.), "Save this application?")]')
        if save_dialog:
            discard_button = driver.find_element(By.XPATH, '//button[contains(., "Discard")]')
            discard_button.click()
            buffer(click_gap)
            print_lg("Handled 'Save this application?' interrupt dialog (Clicked Discard).")
            interrupted = True
    except Exception:
        pass

    return interrupted

def safe_close_modal(driver: WebDriver) -> None:
    '''
    Safely closes any open LinkedIn artdeco-modal and handles follow-up confirmation dialogs.
    '''
    try:
        # Try finding the 'X' (dismiss) button
        dismiss_button = driver.find_elements(By.XPATH, '//button[contains(@aria-label, "Dismiss") or contains(@class, "artdeco-modal__dismiss")]')
        if dismiss_button:
            dismiss_button[0].click()
            buffer(0.5)
            # Check if it triggered a 'Save?' dialog
            handle_interruptModals(driver)
        else:
            # Fallback to ESCAPE key if button not found
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            buffer(0.5)
            handle_interruptModals(driver)
    except Exception as e:
        # print_lg(f"Error while closing modal: {e}")
        pass
