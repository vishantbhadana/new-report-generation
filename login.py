"""
login.py  –  fetch Zerodha Kite *request_token* in Streamlit Cloud
Robust against different Chromium / chromedriver paths.
"""

import os
import time
import logging
import pyotp
from pathlib import Path

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

# ──────────────────────────────────────────────────────────────────────────────
# logging
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
for noisy in ("urllib3", "selenium"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


# ──────────────────────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────────────────────
def _locate_binary(candidates) -> str | None:
    """Return first existing path from *candidates* list, else None."""
    for p in candidates:
        if Path(p).exists():
            return p
    return None


def _new_driver() -> webdriver.Chrome:
    """
    Return a headless Chrome‑driver that works on Streamlit Cloud.

    * binary candidates  : /usr/bin/chromium  | /usr/bin/chromium-browser
    * driver  candidates : /usr/bin/chromedriver | /usr/lib/chromium/chromedriver
    """
    chrome_binary = _locate_binary(
        ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"]
    )
    chromedriver = _locate_binary(
        ["/usr/bin/chromedriver", "/usr/lib/chromium/chromedriver"]
    )

    if not chrome_binary or not chromedriver:
        raise FileNotFoundError(
            f"Cannot find chromium ({chrome_binary}) or chromedriver ({chromedriver})"
        )

    options = Options()
    options.binary_location = chrome_binary
    # “new” headless is default for Chrome ≥ 109
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    service = Service(chromedriver)
    try:
        return webdriver.Chrome(service=service, options=options)
    except WebDriverException as exc:
        # if explicit path still fails, try Selenium‑Manager fallback once
        logging.warning("explicit chromedriver failed → fallback to driverless: %s", exc)
        return webdriver.Chrome(options=options)


# ──────────────────────────────────────────────────────────────────────────────
# main function
# ──────────────────────────────────────────────────────────────────────────────
def kiteLogin(user_id: str, user_pwd: str, totp_key: str, api_key: str) -> str:
    """
    Perform the Zerodha Connect flow and return *request_token*.
    Raise an exception on any failure.
    """
    driver = None
    try:
        driver = _new_driver()
        driver.get(f"https://kite.trade/connect/login?api_key={api_key}&v=3")

        # credentials
        WebDriverWait(driver, 10).until(
            lambda d: d.find_element(By.ID, "userid")
        ).send_keys(user_id)
        driver.find_element(By.ID, "password").send_keys(user_pwd)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()

        # TOTP
        totp_box = WebDriverWait(driver, 10).until(
            lambda d: d.find_element(By.XPATH, '//*[@icon="shield"]')
        )
        totp_box.send_keys(pyotp.TOTP(totp_key).now())

        # wait for redirect containing request_token
        logging.info("waiting for request_token redirect…")
        for _ in range(40):  # ≈20 s
            url = driver.current_url
            if "request_token=" in url:
                token = url.split("request_token=")[1].split("&")[0]
                logging.info("request_token obtained")
                return token
            time.sleep(0.5)

        raise TimeoutException("request_token not found in redirect URL")

    except (SessionNotCreatedException, WebDriverException, TimeoutException) as e:
        logging.error("kiteLogin failed: %s", e)
        raise
    finally:
        if driver:
            driver.quit()


# ──────────────────────────────────────────────────────────────────────────────
# quick manual test (runs only when this file is executed directly)
# ──────────────────────────────────────────────────────────────────────────────
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
