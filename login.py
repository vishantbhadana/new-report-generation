"""
login.py  –  obtain Zerodha Kite *request_token* on Streamlit Cloud
• Works with the chromium/chromedriver you install via packages.txt
• Handles both TOTP and 6‑digit PIN screens
• Extra network‑ready wait logic ==> no more TimeoutException
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

# ───────────────────────────── logging ─────────────────────────────
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
for noisy in ("urllib3", "selenium"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


# ─────────────────────── chromium / driver helpers ─────────────────
def _first_existing(paths: list[str]) -> str | None:
    for p in paths:
        if Path(p).exists():
            return p
    return None


def _make_driver() -> webdriver.Chrome:
    """
    Return headless Chrome set‑up for Streamlit Cloud.

    binary candidates  = /usr/bin/chromium-browser | /usr/bin/chromium
    driver candidates  = /usr/bin/chromedriver     | /usr/lib/chromium/chromedriver
    """
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
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    )
    opts.add_argument("--disable-blink-features=AutomationControlled")

    try:
        serv = Service(chromedriver)
        return webdriver.Chrome(service=serv, options=opts)
    except WebDriverException as e:
        # fallback (driverless) once
        logging.warning("explicit chromedriver failed → fallback: %s", e)
        return webdriver.Chrome(options=opts)


# ───────────────────────── kiteLogin main ──────────────────────────
def kiteLogin(user_id: str, user_pwd: str, totp_key: str, api_key: str) -> str:
    """
    Complete Zerodha Connect login & return *request_token*.
    Raises TimeoutException if any page element does not show up in time.
    """
    driver: webdriver.Chrome | None = None
    try:
        driver = _make_driver()
        driver.set_page_load_timeout(40)
        url_login = f"https://kite.trade/connect/login?api_key={api_key}&v=3"
        driver.get(url_login)

        # 0️⃣ wait for full page load
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        # 1️⃣ credentials screen
        WebDriverWait(driver, 25).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input#userid"))
        ).send_keys(user_id)
        driver.find_element(By.CSS_SELECTOR, "input#password").send_keys(user_pwd)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # 2️⃣ 2‑FA (TOTP or PIN)
        def two_fa_ready(d: webdriver.Chrome):
            return (
                "request_token=" in d.current_url
                or d.find_elements(By.ID, "totp")
                or d.find_elements(By.ID, "pin")
            )

        WebDriverWait(driver, 30).until(two_fa_ready)

        # already redirected?
        if "request_token=" in driver.current_url:
            return driver.current_url.split("request_token=")[1].split("&")[0]

        box = (
            driver.find_element(By.ID, "totp")
            if driver.find_elements(By.ID, "totp")
            else driver.find_element(By.ID, "pin")
        )
        box.send_keys(pyotp.TOTP(totp_key).now())
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # 3️⃣ wait for redirect
        WebDriverWait(driver, 35).until(
            lambda d: "request_token=" in d.current_url
        )
        token = driver.current_url.split("request_token=")[1].split("&")[0]
        logging.info("request_token obtained")
        return token

    except (SessionNotCreatedException, WebDriverException, TimeoutException) as e:
        logging.error("kiteLogin failed: %s", e)
        raise
    finally:
        if driver:
            driver.quit()


# ───────────────────────── self‑test (optional) ────────────────────
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
