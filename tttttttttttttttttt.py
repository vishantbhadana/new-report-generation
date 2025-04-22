from py5paisa import FivePaisaClient
import os

cred = {
    "APP_NAME": os.getenv("APP_NAME"),
    "APP_SOURCE": os.getenv("APP_SOURCE"),
    "USER_ID": os.getenv("USER_ID "),
    "PASSWORD": os.getenv("PASSWORD"),
    "USER_KEY": os.getenv("USER_KEY"),
    "ENCRYPTION_KEY": os.getenv("ENCRYPTION_KEY ")
    }
print(os.getenv("APP_NAME"))
SECRET_KEY = os.getenv("SECRET_KEY")
print(SECRET_KEY)
CLIENT_CODE = os.getenv("CLIENT_CODE")
PIN = os.getenv("PIN")
