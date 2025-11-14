import pymysql
from pymysql.cursors import DictCursor

def get_connection():
    try:
        conn = pymysql.connect(
            host="localhost",
            user="root",
            password="password",
            database = "student",
            port=3306,
            cursorclass=DictCursor
        )
        return conn
    except Exception as e:
        print("Database connection failed:", e)
        return None