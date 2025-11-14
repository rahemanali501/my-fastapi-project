import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv
import os
import ssl  # Required for secure cloud database connections (like Aiven)

load_dotenv()  # Load environment variables from .env for local development

def get_connection():
    # --- Aiven SSL Configuration ---
    # Create an SSL context that does not verify the server's certificate.
    # This is an easier setup for cloud DBs that enforce SSL.
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        # Attempt to connect to the database
        conn = pymysql.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            port=int(os.getenv("DB_PORT")),  # Port must be an integer
            cursorclass=DictCursor,  # Returns results as dictionaries
            ssl=ssl_context,  # Apply the custom SSL settings

            # --- FIX FOR 502 ERROR ---
            # Increase timeout to 10 seconds for slow cloud connections
            connect_timeout=10
        )
        return conn
    except Exception as e:
        # Print the specific error to the console/logs if connection fails
        print(f"DATABASE CONNECTION FAILED: {e}")
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