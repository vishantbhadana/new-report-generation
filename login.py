"""
login.py – fetch Zerodha Kite request_token on Streamlit Cloud
• Uses container’s chromium/chromedriver (add both in packages.txt)
• Robust: polls up to 90 s for each required element
• On ultimate failure, saves page HTML to help debug
"""

from __future__ import annotations
import os, time, logging, sys
from pathlib import Path
import pyotp

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException

# ─────────── logging ───────────
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

# ─────────── helpers ───────────
def _first_existing(paths: list[str]) -> str | None:
    return next((p for p in paths if Path(p).exists()), None)

def _new_driver() -> webdriver.Chrome:
    chrome_bin  = _first_existing(["/usr/bin/chromium-browser", "/usr/bin/chromium"])
    chromedriver = _first_existing(["/usr/bin/chromedriver", "/usr/lib/chromium/chromedriver"])
    if not chrome_bin or not chromedriver:
        raise FileNotFoundError("chromium or chromedriver missing in container")

    opts = Options()
    opts.binary_location = chrome_bin
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(chromedriver), options=opts)

def _poll_for(driver, css_list: list[str], timeout: int = 90):
    """Return first matching element (polls every 0.5 s) or raise TimeoutException."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for sel in css_list:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if els:
                return els[0]
        time.sleep(0.5)
    raise TimeoutException(f"None of {css_list} appeared in {timeout}s")

# ─────────── main ───────────
def kiteLogin(user_id: str, user_pwd: str, totp_key: str, api_key: str) -> str:
    driver: webdriver.Chrome | None = None
    try:
        driver = _new_driver()
        driver.get(f"https://kite.trade/connect/login?api_key={api_key}&v=3")

        # 1️⃣ credentials
        _poll_for(driver, ["input#userid", "input[name='user_id']", "input[name='userid']"]).send_keys(user_id)
        driver.find_element(By.CSS_SELECTOR, "input#password").send_keys(user_pwd)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # 2️⃣ 2‑FA   (may redirect instantly)
        if "request_token=" not in driver.current_url:
            _poll_for(driver, ["input#totp", "input#pin"])
            box = driver.find_element(By.CSS_SELECTOR, "input#totp, input#pin")
            box.send_keys(pyotp.TOTP(totp_key).now())
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # 3️⃣ wait for redirect
        deadline = time.time() + 90
        while time.time() < deadline:
            url = driver.current_url
            if "request_token=" in url:
                return url.split("request_token=")[1].split("&")[0]
            time.sleep(0.5)

        raise TimeoutException("redirect with request_token never happened")

    except TimeoutException as e:
        # write page HTML to help diagnose unexpected layout changes
        if driver:
            dump = "/tmp/kite_login_fail.html
