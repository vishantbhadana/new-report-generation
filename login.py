"""
login.py – get Zerodha Kite *request_token* on Streamlit Cloud
• Uses container’s chromium/chromedriver (install them in packages.txt)
• Works with both TOTP and 6‑digit PIN screens
"""

from __future__ import annotations

import os, time, logging
from pathlib import Path

import pyotp
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    SessionNotCreatedException,
    TimeoutException,
    WebDriverException,
)

# ───────────────────────── logging ─────────────────────────
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
for noisy in ("urllib3", "selenium"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# ─────────────────── chromium helpers ──────────────────────
def _first_existing(paths: list[str]) -> str | None:
    for p in paths:
        if Path(p).exists():
            return p
    return None


def _make_driver() -> webdriver.Chrome:
    chrome_bin = _first_existing(
        ["/usr/bin/chromium-browser", "/usr/bin/chromium"]
    )
    chromedriver = _first_existing(
        ["/usr/bin/chromedriver", "/usr/lib/chromium/chromedriver"]
    )
    if not chrome_bin or not chromedriver:
        raise FileNotFoundError("chromium/chromedriver not found in container")

    opts = Options()
    opts.binary_location = chrome_bin
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")

    try:
        return webdriver.Chrome(service=Service(chromedriver), options=opts)
    except WebDriverException:
        return webdriver.Chrome(options=opts)        # fall back

# ──────────────────── main function ───────────────────────
def kiteLogin(user_id: str, user_pwd: str, totp_key: str, api_key: str) -> str:
    """Return Zerodha *request_token*; raises on failure."""
    driver: webdriver.Chrome | None = None
    try:
        driver = _make_driver()
        driver.set_page_load_timeout(45)
        driver.get(f"https://kite.trade/connect/login?api_key={api_key}&v=3")

        # user‑id box (robust selector list, 60‑s wait)
        def _userid_box(d):
            selectors = (
                "input#userid",
                "input[name='user_id']",
                "input[name='userid']",
                "input[placeholder='User ID']",
            )
            for css in selectors:
                els = d.find_elements(By.CSS_SELECTOR, css)
                if els:
                    return els[0]
            return False

        WebDriverWait(driver, 60).until(_userid_box).send_keys(user_id)
        driver.find_element(By.CSS_SELECTOR, "input#password").send_keys(user_pwd)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # 2‑FA page (TOTP or PIN)
        def _2fa_ready(d: webdriver.Chrome):
            return (
                "request_token=" in d.current_url
                or d.find_elements(By.ID, "totp")
                or d.find_elements(By.ID, "pin")
            )

        WebDriverWait(driver, 60).until(_2fa_ready)

        if "request_token=" in driver.current_url:
            return driver.current_url.split("request_token=")[1].split("&")[0]

        box = (
            driver.find_element(By.ID, "totp")
            if driver.find_elements(By.ID, "totp")
            else driver.find_element(By.ID, "pin")
        )
        box.send_keys(pyotp.TOTP(totp_key).now())
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        WebDriverWait(driver, 60).until(
            lambda d: "request_token=" in d.current_url
        )
        return driver.current_url.split("request_token=")[1].split("&")[0]

    except (SessionNotCreatedException, WebDriverException, TimeoutException) as e:
        logging.error("kiteLogin failed: %s", e)
        raise
    finally:
        if driver:
            driver.quit()

# self‑test (run locally if env vars are set)
if __name__ == "__main__":
    try:
        tok = kiteLogin(
            os.getenv("user_name"),
            os.getenv("password"),
            os.getenv("totp"),
            os.getenv("api_key"),
        )
        print("request_token =", tok)
    except Exception as err:
        print("login.py self‑test failed:", err)
