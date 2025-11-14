import os
import pymysql
from pymysql.cursors import DictCursor
from urllib.parse import urlparse, unquote

def get_connection():
    try:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise Exception("DATABASE_URL environment variable not found")

        # parse the URL (supports mysql:// and mysql+pymysql://)
        url = urlparse(db_url)

        # extract values and unquote percent-encoded parts
        host = url.hostname
        user = unquote(url.username) if url.username else None
        password = unquote(url.password) if url.password else None
        database = url.path.lstrip("/") if url.path else None
        port = url.port or 3306

        if not all([host, user, password, database]):
            raise Exception("DATABASE_URL seems incomplete (host/user/password/database required)")

        # Aiven requires SSL — pass a minimal ssl dict (PyMySQL accepts this)
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=int(port),
            cursorclass=DictCursor,
            ssl={"ssl": {}}   # enable SSL (Aiven requires)
        )

        return conn

    except Exception as e:
        # print for logs (Render logs will show this)
        print("Database connection failed:", e)
        return None
