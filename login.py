"""
login.py  –  obtain Zerodha Kite *request_token* in Streamlit Cloud
• Works with Chromium / chromedriver that you install via packages.txt
• Handles either TOTP box id="totp"  or  PIN box id="pin"
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
    Return headless Chrome suited for Streamlit Cloud.

    binary candidates  = /usr/bin/chromium-browser  | /usr/bin/chromium
    driver candidates  = /usr/bin/chromedriver      | /usr/lib/chromium/chromedriver
    """
    chrome_bin = _first_existing(
        ["/usr/bin/chromium-browser", "/usr/bin/chromium", "/usr/bin/google-chrome"]
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

    try:
        serv = Service(chromedriver)
        return webdriver.Chrome(service=serv, options=opts)
    except WebDriverException as e:
        # fall back on Selenium‑Manager (driverless) once
        logging.warning("explicit chromedriver failed → selenium‑manager fallback (%s)", e)
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
        driver.get(f"https://kite.trade/connect/login?api_key={api_key}&v=3")

        # ── 1  credentials page ─────────────────────────────────────
        WebDriverWait(driver, 15).until(
            lambda d: d.find_element(By.ID, "userid")
        ).send_keys(user_id)
        driver.find_element(By.ID, "password").send_keys(user_pwd)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()

        # ── 2  2‑FA page (TOTP or PIN) ──────────────────────────────
        def _2fa_ready(d: webdriver.Chrome):
            return (
                "request_token=" in d.current_url
                or d.find_elements(By.ID, "totp")
                or d.find_elements(By.ID, "pin")
            )

        WebDriverWait(driver, 20).until(_2fa_ready)

        # If redirect already happened very fast
        if "request_token=" in driver.current_url:
            return driver.current_url.split("request_token=")[1].split("&")[0]

        # otherwise fill 2‑FA
        box = (
            driver.find_element(By.ID, "totp")
            if driver.find_elements(By.ID, "totp")
            else driver.find_element(By.ID, "pin")
        )
        box.send_keys(pyotp.TOTP(totp_key).now())
        driver.find_element(By.XPATH, "//button[@type='submit']").click()

        # ── 3  wait for redirect with token ─────────────────────────
        WebDriverWait(driver, 25).until(
            lambda d: "request_token=" in d.current_url
        )
        token = driver.current_url.split("request_token=")[1].split("&")[0]
        logging.info("request_token acquired")
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
