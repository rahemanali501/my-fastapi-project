import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv
import os
import ssl  # Ye naya import zaroori hai Aiven ke liye

load_dotenv() 

def get_connection():
    # SSL Context create karein jo verify na kare (Easy mode for Aiven)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            port=int(os.getenv("DB_PORT")), # Port ko int banana zaroori hai
            cursorclass=DictCursor,
            ssl=ssl_context  # Yahan humne apna custom SSL logic lagaya
        )
        return conn
    except Exception as e:
        print("Database connection failed:", e)
        return None





























# import pymysql
# from pymysql.cursors import DictCursor

# def get_connection():
#     try:
#         conn = pymysql.connect(
#             host="localhost",
#             user="root",
#             password="password",
#             database = "student",
#             port=3306,
#             cursorclass=DictCursor
#         )
#         return conn
#     except Exception as e:
#         print("Database connection failed:", e)
#         return None