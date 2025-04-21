"""
login.py – returns Zerodha Kite request_token

• Detects platform:
    ‑ macOS   → uses Google Chrome + /usr/local/bin/chromedriver
    ‑ Linux   → uses the chromium/chromedriver you install via packages.txt

• Handles both TOTP and 6‑digit PIN 2‑FA pages
• Polls patiently (90 s) to avoid TimeoutException
• On ultimate failure dumps the HTML to /tmp/kite_login_fail.html for inspection
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

# ───────────────────────── logging ─────────────────────────
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
for noisy in ("urllib3", "selenium"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


# ─────────────────── path detection ───────────────────────
def _detect_paths() -> tuple[str, str]:
    """Return (chrome_binary, chromedriver_binary). Raises FileNotFoundError."""
    if platform.system() == "Darwin":          # macOS laptop
        chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        driver = "/usr/local/bin/chromedriver"
        if Path(chrome).exists() and Path(driver).exists():
            return chrome, driver

    # default Linux / Streamlit Cloud paths
    chrome = next((p for p in ("/usr/bin/chromium-browser", "/usr/bin/chromium") if Path(p).exists()), None)
    driver = next((p for p in ("/usr/bin/chromedriver", "/usr/lib/chromium/chromedriver") if Path(p).exists()), None)
    if chrome and driver:
        return chrome, driver

    raise FileNotFoundError("Could not locate Chrome/Chromium and chromedriver.")


# ─────────────────── webdriver helper ──────────────────────
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
        # fallback to Selenium‑Manager (driverless) once
        return webdriver.Chrome(options=opts)


# ─────────────────── polling utility ──────────────────────
def _poll_for_css(driver: webdriver.Chrome, selectors: list[str], timeout: int = 90):
    """Return first WebElement that appears within *timeout* seconds, else raise."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for css in selectors:
            els = driver.find_elements(By.CSS_SELECTOR, css)
            if els:
                return els[0]
        time.sleep(0.5)
    raise TimeoutException(f"None of selectors {selectors} appeared in {timeout}s")


# ─────────────────── main login function ──────────────────
def kiteLogin(user_id: str, user_pwd: str, totp_key: str, api_key: str) -> str:
    """Return Zerodha Connect *request_token*."""
    drv: webdriver.Chrome | None = None
    try:
        drv = _new_driver()
        drv.get(f"https://kite.trade/connect/login?api_key={api_key}&v=3")

        # 1️⃣ credentials page
        _poll_for_css(
            drv,
            ["input#userid", "input[name='user_id']", "input[name='userid']", "input[placeholder='User ID']"],
        ).send_keys(user_id)
        drv.find_element(By.CSS_SELECTOR, "input#password").send_keys(user_pwd)
        drv.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # 2️⃣ 2‑FA (TOTP or PIN) – might redirect instantly
        if "request_token=" not in drv.current_url:
            _poll_for_css(drv, ["input#totp", "input#pin"])
            drv.find_element(By.CSS_SELECTOR, "input#totp, input#pin").send_keys(pyotp.TOTP(totp_key).now())
            drv.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # 3️⃣ wait for redirect
        deadline = time.time() + 90
        while time.time() < deadline:
            url = drv.current_url
            if "request_token=" in url:
                token = url.split("request_token=")[1].split("&")[0]
                logging.info("request_token acquired")
                return token
            time.sleep(0.5)

        raise TimeoutException("Redirect with request_token never happened.")

    except TimeoutException as e:
        if drv:
            dump = "/tmp/kite_login_fail.html"
            Path(dump).write_text(drv.page_source, encoding="utf-8")
            logging.error("Timeout – page dumped to %s", dump)
        raise e
    finally:
        if drv:
            drv.quit()


# ─────────────────── self‑test (optional) ──────────────────
if __name__ == "__main__":
    try:
        tok = kiteLogin(
            os.getenv("user_name"), os.getenv("password"),
            os.getenv("totp"),      os.getenv("api_key"),
        )
        print("request_token:", tok)
    except Exception as exc:
        print("login failed:", exc, file=sys.stderr)
