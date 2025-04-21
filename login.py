"""
login.py  –  get Zerodha Kite *request_token* in headless mode
Compatible with Streamlit Cloud (uses the system‑supplied Chromium + chromedriver)
"""

import time
import logging
import pyotp

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import SessionNotCreatedException, TimeoutException, WebDriverException

# ──────────────────────────────────────────────────────────────────────────────
# basic logging
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("selenium").setLevel(logging.WARNING)


def _new_driver() -> webdriver.Chrome:
    """
    Return a headless Chrome driver that works on Streamlit Cloud.

    Assumes:
    * Chromium binary   → /usr/bin/chromium‑browser   (or /usr/bin/chromium)
    * Chromedriver      → /usr/bin/chromedriver
    Both come from **packages.txt** lines:
        chromium
        chromium-driver
    """
    options = Options()
    options.binary_location = "/usr/bin/chromium-browser"  # fallback path below
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # if SL image has /usr/bin/chromium instead:
    if not Service.is_connectable:
        import os
        if os.path.exists("/usr/bin/chromium"):
            options.binary_location = "/usr/bin/chromium"

    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)


def kiteLogin(user_id: str, user_pwd: str, totp_key: str, api_key: str) -> str:
    """
    Launch the Zerodha Connect login flow and return the *request_token*.
    Raises on any failure.
    """
    driver = None
    try:
        driver = _new_driver()
        driver.get(f"https://kite.trade/connect/login?api_key={api_key}&v=3")

        # 1 – credentials
        WebDriverWait(driver, 10).until(
            lambda d: d.find_element(By.ID, "userid")
        ).send_keys(user_id)

        driver.find_element(By.ID, "password").send_keys(user_pwd)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()

        # 2 – TOTP
        totp_box = WebDriverWait(driver, 10).until(
            lambda d: d.find_element(By.XPATH, '//*[@icon="shield"]')
        )
        totp_box.send_keys(pyotp.TOTP(totp_key).now())

        # 3 – wait for redirect containing request_token
        logging.info("waiting for redirect…")
        for _ in range(40):        # ≈ 20 s
            url = driver.current_url
            if "request_token=" in url:
                token = url.split("request_token=")[1].split("&")[0]
                logging.info("token obtained")
                return token
            time.sleep(0.5)

        raise TimeoutException("request_token not found in redirect URL")

    except (SessionNotCreatedException, WebDriverException) as e:
        logging.error("chromedriver error: %s", e)
        raise
    finally:
        if driver:
            driver.quit()


# quick manual test
if __name__ == "__main__":
    import os
    try:
        token = kiteLogin(
            os.getenv("user_name"),
            os.getenv("password"),
            os.getenv("totp"),
            os.getenv("api_key"),
        )
        print("request_token →", token)
    except Exception as exc:
        print("login failed:", exc)
