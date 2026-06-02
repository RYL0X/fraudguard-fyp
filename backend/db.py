"""
Database connection helper.
Reads credentials from .env at the project root.
"""
import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load .env from project root (two levels up from this file)
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_root, '.env'))


def get_connection():
    """Return a live MySQL connection, or raise a clear error."""
    try:
        return mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'fraud_detection'),
        )
    except Error as exc:
        raise RuntimeError(f"DB connection failed: {exc}") from exc
