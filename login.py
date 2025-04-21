from __future__ import annotations
import os, time, logging, sys
from pathlib import Path
import pyotp
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

def _first_existing(paths: list[str]) -> str | None:
    return next((p for p in paths if Path(p).exists()), None)

def _new_driver() -> webdriver.Chrome:
    chrome_bin = _first_existing(["/usr/bin/chromium-browser", "/usr/bin/chromium"])
    chromedriver = _first_existing(["/usr/bin/chromedriver", "/usr/lib/chromium/chromedriver"])
    if not chrome_bin or not chromedriver:
        raise FileNotFoundError("chromium or chromedriver missing in container")

    opts = Options()
    opts.binary_location = chrome_bin
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-infobars")
    opts.add_argument("--start-maximized")
    opts.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(chromedriver), options=opts)

def _poll_for(driver, css_list: list[str], timeout: int = 120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for sel in css_list:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if els:
                return els[0]
        time.sleep(0.5)
    raise TimeoutException(f"None of {css_list} appeared in {timeout}s")

def kiteLogin(user_id: str, user_pwd: str, totp_key: str, api_key: str) -> str:
    driver: webdriver.Chrome | None = None
    try:
        driver = _new_driver()
        driver.get(f"https://kite.trade/connect/login?api_key={api_key}&v=3")

        # 1️⃣ credentials
        _poll_for(driver, ["input#userid", "input[name='user_id']", "input[name='userid']"]).send_keys(user_id)
        _poll_for(driver, ["input#password", "input[name='password']"]).send_keys(user_pwd)
        _poll_for(driver, ["button[type='submit']", "button.login-button"]).click()

        # 2️⃣ 2-FA (may redirect instantly)
        if "request_token=" not in driver.current_url:
            _poll_for(driver, ["input#totp", "input#pin", "input[name='twofa_value']"])
            box = driver.find_element(By.CSS_SELECTOR, "input#totp, input#pin, input[name='twofa_value']")
            box.send_keys(pyotp.TOTP(totp_key).now())
            _poll_for(driver, ["button[type='submit']", "button.login-button"]).click()

        # 3️⃣ wait for redirect
        deadline = time.time() + 120
        while time.time() < deadline:
            url = driver.current_url
            if "request_token=" in url:
                return url.split("request_token=")[1].split("&")[0]
            time.sleep(0.5)

        raise TimeoutException("redirect with request_token never happened")

    except TimeoutException as e:
        if driver:
            with open("/tmp/kite_login_fail.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            logging.error("Timeout occurred. Page source saved to /tmp/kite_login_fail.html")
        raise
    finally:
        if driver:
            driver.quit()