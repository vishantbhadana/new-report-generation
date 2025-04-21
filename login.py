"""
login.py – return Zerodha Kite *request_token*

• Works on macOS and Streamlit Cloud
• No webdriver‑manager; we point to fixed driver paths
• Robust selectors list + 90‑s polling eliminates timeout
• Dumps failure page to /tmp/kite_login_fail.html for debugging
"""

from __future__ import annotations
import os, sys, time, platform, logging
from pathlib import Path
import pyotp

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException


# ─────────────────────────── logging ────────────────────────────
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
for noisy in ("urllib3", "selenium"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


# ─────────── find browser + driver depending on platform ─────────
def _detect_paths() -> tuple[str, str]:
    """Return (chrome_binary, chromedriver_binary)."""
    if platform.system() == "Darwin":  # macOS
        chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        driver = "/usr/local/bin/chromedriver"
        if Path(chrome).exists() and Path(driver).exists():
            return chrome, driver

    # Linux / Streamlit Cloud container
    chrome = next((p for p in ("/usr/bin/chromium-browser", "/usr/bin/chromium")
                   if Path(p).exists()), None)
    driver = next((p for p in ("/usr/bin/chromedriver", "/usr/lib/chromium/chromedriver")
                   if Path(p).exists()), None)
    if chrome and driver:
        return chrome, driver

    raise FileNotFoundError("Chrome/Chromium and chromedriver not found.")


# ────────────────── webdriver factory ────────────────────────────
def _new_driver() -> webdriver.Chrome:
    chrome_bin, driver_bin = _detect_paths()

    opts = Options()
    opts.binary_location = chrome_bin
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")

    try:
        return webdriver.Chrome(service=Service(driver_bin), options=opts)
    except WebDriverException:
        # fall back to Selenium‑Manager once (not used on Cloud)
        return webdriver.Chrome(options=opts)


# ─────────────── polling helper (0.5 s steps) ────────────────────
def _poll_for_css(driver, selectors: list[str], timeout: int = 90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for sel in selectors:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if els:
                return els[0]
        time.sleep(0.5)
    raise TimeoutException(f"{selectors} not found in {timeout}s")


# ─────────────────────── main login fn ───────────────────────────
def kiteLogin(user_id: str, user_pwd: str, totp_key: str, api_key: str) -> str:
    drv: webdriver.Chrome | None = None
    try:
        drv = _new_driver()
        drv.get(f"https://kite.trade/connect/login?api_key={api_key}&v=3")

        # 1️⃣ credential page
        _poll_for_css(
            drv,
            ["input#userid", "input[name='user_id']", "input[name='userid']",
             "input[placeholder='User ID']"]
        ).send_keys(user_id)
        drv.find_element(By.CSS_SELECTOR, "input#password").send_keys(user_pwd)
        drv.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # 2️⃣ 2‑FA (may already redirect)
        if "request_token=" not in drv.current_url:
            _poll_for_css(drv, ["input#totp", "input#pin"])
            drv.find_element(By.CSS_SELECTOR, "input#totp, input#pin")\
               .send_keys(pyotp.TOTP(totp_key).now())
            drv.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # 3️⃣ wait for redirect
        deadline = time.time() + 90
        while time.time() < deadline:
            url = drv.current_url
            if "request_token=" in url:
                return url.split("request_token=")[1].split("&")[0]
            time.sleep(0.5)

        raise TimeoutException("request_token redirect never happened.")

    except TimeoutException as e:
        if drv:
            Path("/tmp/kite_login_fail.html").write_text(drv.page_source,
                                                         encoding="utf-8")
            logging.error("Timeout – HTML dumped to /tmp/kite_login_fail.html")
        raise e
    finally:
        if drv:
            drv.quit()


# ───────────────────────── self‑test ─────────────────────────────
if __name__ == "__main__":
    try:
        print("request_token →",
              kiteLogin(os.getenv("user_name"),
                        os.getenv("password"),
                        os.getenv("totp"),
                        os.getenv("api_key")))
    except Exception as err:
        print("login failed:", err, file=sys.stderr)
