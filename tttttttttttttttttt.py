"""
login.py – return Zerodha Kite *request_token*
• Works on macOS and Streamlit Cloud
• Uses direct paths for both Chromium and chromedriver
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
from selenium.common.exceptions import TimeoutException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _new_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')

    # ✅ Correct Chromium binary and chromedriver path
    options.binary_location = "/Applications/Chromium.app/Contents/MacOS/Chromium"
    service = Service(executable_path="/usr/local/bin/chromedriver")

    return webdriver.Chrome(service=service, options=options)

def kiteLogin(user_id: str, user_pwd: str, totp_key: str, api_key: str) -> str:
    """Return the Kite request token after logging in."""
    driver = None
    try:
        driver = _new_driver()
        driver.get(f"https://kite.trade/connect/login?api_key={api_key}&v=3")

        WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input#userid"))).send_keys(user_id)
        driver.find_element(By.CSS_SELECTOR, "input#password").send_keys(user_pwd)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        totp = pyotp.TOTP(totp_key).now()
        WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[icon='shield']"))).send_keys(totp)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        logger.info("⌛ Waiting for request_token in redirected URL...")
        for _ in range(90):
            if "request_token=" in driver.current_url:
                break
            time.sleep(1)

        final_url = driver.current_url
        if "request_token=" not in final_url:
            raise TimeoutException("request_token not found in URL")

        request_token = final_url.split("request_token=")[1].split("&")[0]
        logger.info("✅ Login successful. Request token obtained.")
        return request_token

    except Exception as e:
        logger.exception("❌ Error during login: %s", e)
        if driver:
            with open("/tmp/kite_login_fail.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        raise

    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    token = kiteLogin(
        user_id=os.getenv("user_name"),
        user_pwd=os.getenv("password"),
        totp_key=os.getenv("totp"),
        api_key=os.getenv("api_key")
    )
    print("Token:", token)
