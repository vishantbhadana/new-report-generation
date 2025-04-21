# login.py
import time, pyotp, logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def _new_driver():
    chrome_path = "/usr/bin/chromedriver"  # ✅ For Streamlit Cloud
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(executable_path=chrome_path)
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def kiteLogin(user_id, user_pwd, totp_key, api_key):
    try:
        driver = _new_driver()
        driver.get(f'https://kite.trade/connect/login?api_key={api_key}&v=3')

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "userid"))
        ).send_keys(user_id)

        driver.find_element(By.ID, "password").send_keys(user_pwd)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[icon='shield']"))
        ).send_keys(pyotp.TOTP(totp_key).now())

        time.sleep(1)
        url = ""
        for _ in range(90):
            if "request_token=" in driver.current_url:
                url = driver.current_url
                break
            time.sleep(1)

        driver.quit()

        if "request_token=" not in url:
            raise Exception("Request token not found in URL")

        return url.split("request_token=")[1].split("&")[0]

    except Exception as e:
        logging.error(f"❌ Error during login: {e}")
        raise
