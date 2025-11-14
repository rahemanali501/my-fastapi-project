import os
import pymysql
from pymysql.cursors import DictCursor
from urllib.parse import urlparse, unquote, parse_qs

def get_connection():
    """
    Prefer DATABASE_URL (Render/Aiven). If not set, fallback to local MySQL.
    DATABASE_URL example:
    mysql+pymysql://avnadmin:PASS@mysql-...aivencloud.com:18181/defaultdb?ssl-mode=REQUIRED
    """
    try:
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            url = urlparse(db_url)

            host = url.hostname
            user = unquote(url.username) if url.username else None
            password = unquote(url.password) if url.password else None
            database = url.path.lstrip("/") if url.path else None
            port = url.port or 3306

            # detect if ssl-mode is required in query params (Aiven uses ssl-mode=REQUIRED)
            qs = parse_qs(url.query)
            need_ssl = any(k.lower().startswith("ssl") or "ssl-mode" in k.lower() for k in qs) or ("ssl-mode" in url.query.lower())

            connect_kwargs = dict(
                host=host,
                user=user,
                password=password,
                database=database,
                port=int(port),
                cursorclass=DictCursor,
            )
            if need_ssl:
                connect_kwargs["ssl"] = {"ssl": {}}

            conn = pymysql.connect(**connect_kwargs)
            return conn

        # FALLBACK: local development settings (only used when DATABASE_URL not provided)
        conn = pymysql.connect(
            host="localhost",
            user="root",
            password="password",   # your local password
            database="student",
            port=3306,
            cursorclass=DictCursor
        )
        return conn

    except Exception as e:
        # Print to logs so Render/VSCode terminal shows it
        print("Database connection failed:", e)
        return None








































# OLD local connection code (commented out)

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