"""
One-time database setup script.
  1. Creates the `fraud_detection` database (if absent).
  2. Creates the `transactions` table.
  3. Bulk-loads data/transactions.csv (run generate_data.py first).

Usage (from project root):
    python backend/setup_db.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASS = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'fraud_detection')

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS transactions (
    id            VARCHAR(36)    PRIMARY KEY,
    user_id       INT            NOT NULL,
    amount        DECIMAL(10,2)  NOT NULL,
    merchant      VARCHAR(255),
    category      VARCHAR(50),
    timestamp     DATETIME,
    location      VARCHAR(100),
    is_foreign    TINYINT(1)     DEFAULT 0,
    hour          TINYINT        DEFAULT 0,
    day_of_week   TINYINT        DEFAULT 0,
    is_fraud      TINYINT(1)     DEFAULT 0,
    predicted_fraud TINYINT(1)   DEFAULT NULL,
    confidence    DECIMAL(6,4)   DEFAULT NULL,
    created_at    TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

INSERT_SQL = """
INSERT IGNORE INTO transactions
    (id, user_id, amount, merchant, category, timestamp,
     location, is_foreign, hour, day_of_week, is_fraud)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def main():
    # ── Connect without database to create it ──────────────────────────────
    root_conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS)
    cur = root_conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    root_conn.commit()
    cur.close()
    root_conn.close()
    print(f"✅ Database `{DB_NAME}` ready.")

    # ── Connect to the target database ─────────────────────────────────────
    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER,
                                   password=DB_PASS, database=DB_NAME)
    cur  = conn.cursor()
    cur.execute(CREATE_TABLE)
    conn.commit()
    print("✅ Table `transactions` ready.")

    # ── Load CSV ────────────────────────────────────────────────────────────
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'data', 'transactions.csv')
    if not os.path.exists(csv_path):
        print("⚠️  data/transactions.csv not found — run `python simulation/generate_data.py` first.")
        return

    df = pd.read_csv(csv_path)
    records = [
        (row['transaction_id'], int(row['user_id']), float(row['amount']),
         row['merchant'], row['category'], row['timestamp'], row['location'],
         int(row['is_foreign']), int(row['hour']), int(row['day_of_week']),
         int(row['is_fraud']))
        for _, row in df.iterrows()
    ]

    cur.executemany(INSERT_SQL, records)
    conn.commit()
    print(f"✅ Inserted {cur.rowcount:,} rows.")
    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
