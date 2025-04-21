import time, pyotp, os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_chrome_driver():
    """Start a headless Chrome WebDriver"""
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--window-size=1920x1080')

    # Required in Streamlit Cloud
    chrome_path = '/usr/bin/chromedriver'
    service = Service(executable_path=chrome_path)

    return webdriver.Chrome(service=service, options=chrome_options)

def kiteLogin(user_id, user_pwd, totp_key, api_key):
    url = f"https://kite.trade/connect/login?api_key={api_key}&v=3"
    driver = get_chrome_driver()
    driver.get(url)

    try:
        # Login page
        WebDriverWait(driver, 25).until(EC.presence_of_element_located((By.ID, "userid"))).send_keys(user_id)
        driver.find_element(By.ID, "password").send_keys(user_pwd)
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()

        # TOTP page
        totp = pyotp.TOTP(totp_key).now()
        WebDriverWait(driver, 25).until(EC.presence_of_element_located((By.XPATH, '//input[@type="text"]'))).send_keys(totp)
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()

        # Wait for redirect
        WebDriverWait(driver, 90).until(lambda d: "request_token=" in d.current_url)

        token = driver.current_url.split("request_token=")[-1].split("&")[0]
        driver.quit()
        return token

    except Exception as e:
        # Save page if it fails
        Path("/tmp/kite_login_fail.html").write_text(driver.page_source)
        driver.quit()
        raise Exception(f"Login failed: {e}")
