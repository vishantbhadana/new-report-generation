"""Module to get request token """
import time
import logging
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import SessionNotCreatedException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import pyotp

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("requests").setLevel(logging.WARNING)

def kiteLogin(user_id, user_pwd, totp_key, api_key):
    """Function to get request token """
    max_tries = 20
    count = 0
    driver = None
    try:
        # Set up Chrome options for Streamlit Cloud
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Run in headless mode
        options.add_argument("--no-sandbox")  # Required for Linux environments
        options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource issues
        options.add_argument("--disable-gpu")  # Disable GPU acceleration
        options.add_argument("--window-size=1920x1080")  # Set window size for consistency

        # Use webdriver-manager to handle ChromeDriver
        logging.info("Initializing Chrome WebDriver")
        service = Service(ChromeDriverManager().install())
        logging.info("ChromeDriver path: %s", service.path)
        driver = webdriver.Chrome(service=service, options=options)
        logging.info("WebDriver initialized successfully")

        # Navigate to Kite login page
        driver.get(f'https://kite.trade/connect/login?api_key={api_key}&v=3')
        
        # Enter user ID
        logging.info("Entering user ID")
        login_id = WebDriverWait(driver, 10).until(
            lambda x: x.find_element(By.XPATH, '//*[@id="userid"]'))
        login_id.send_keys(user_id)

        # Enter password
        logging.info("Entering password")
        pwd = WebDriverWait(driver, 10).until(
            lambda x: x.find_element(By.XPATH, '//*[@id="password"]'))
        pwd.send_keys(user_pwd)

        # Click submit button
        logging.info("Submitting login form")
        submit = WebDriverWait(driver, 10).until(
            lambda x: x.find_element(By.XPATH, '//*[@id="container"]/div/div/div[2]/form/div[4]/button'))
        submit.click()

        # Enter TOTP
        logging.info("Entering TOTP")
        totp = WebDriverWait(driver, 10).until(
            lambda x: x.find_element(By.XPATH, '//*[@icon="shield"]'))
        authkey = pyotp.TOTP(totp_key)
        toSendAuthKey = authkey.now()
        totp.send_keys(toSendAuthKey)

        # Wait for redirect with request token
        logging.info("Waiting for request token in URL")
        url = ""
        while count < max_tries:
            time.sleep(0.5)
            url = driver.current_url
            if "request_token=" in url:
                break
            count += 1
        else:
            raise TimeoutException("Failed to retrieve request token within max tries")

        # Extract request token
        initial_token = url.split('request_token=')[1]
        request_token = initial_token.split('&')[0]
        logging.info("Request token retrieved: %s", request_token)

        return request_token

    except SessionNotCreatedException as e:
        logging.error("SessionNotCreatedException: %s", e)
        raise
    except TimeoutException as e:
        logging.error("TimeoutException: %s", e)
        raise
    except Exception as e:
        logging.error("Unexpected error: %s", e)
        raise
    finally:
        if driver:
            logging.info("Closing WebDriver")
            driver.quit()

if __name__ == "__main__":
    pass