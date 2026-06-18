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
    confidence    FLOAT          DEFAULT 0,
    risk_level    VARCHAR(50)    DEFAULT 'LOW',
    source        VARCHAR(50)    DEFAULT 'system',
    decision      VARCHAR(50)    DEFAULT 'approved',
    customer_name VARCHAR(100)   NULL,
    customer_email VARCHAR(150)  NULL,
    card_last4    VARCHAR(10)    NULL,
    created_at    TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

CREATE_ALERTS_TABLE = """
CREATE TABLE IF NOT EXISTS alerts (
    id VARCHAR(64) PRIMARY KEY,
    transaction_id VARCHAR(64),
    amount DECIMAL(12,2),
    merchant VARCHAR(255),
    category VARCHAR(100),
    location VARCHAR(255),
    risk_score FLOAT,
    risk_level VARCHAR(50),
    status VARCHAR(50) DEFAULT 'new',
    source VARCHAR(50),
    message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME NULL,
    resolved_at DATETIME NULL
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
    cur.execute(CREATE_ALERTS_TABLE)
    conn.commit()
    print("✅ Tables `transactions` and `alerts` ready.")

    # ── Safe ALTER TABLE logic for missing columns in transactions ────
    alter_queries = [
        "ALTER TABLE transactions ADD COLUMN confidence FLOAT DEFAULT 0",
        "ALTER TABLE transactions ADD COLUMN risk_level VARCHAR(50) DEFAULT 'LOW'",
        "ALTER TABLE transactions ADD COLUMN source VARCHAR(50) DEFAULT 'system'",
        "ALTER TABLE transactions ADD COLUMN decision VARCHAR(50) DEFAULT 'approved'",
        "ALTER TABLE transactions ADD COLUMN customer_name VARCHAR(100) NULL",
        "ALTER TABLE transactions ADD COLUMN customer_email VARCHAR(150) NULL",
        "ALTER TABLE transactions ADD COLUMN card_last4 VARCHAR(10) NULL"
    ]
    
    for query in alter_queries:
        try:
            cur.execute(query)
        except mysql.connector.Error as err:
            # 1060 is the error code for "Duplicate column name"
            if err.errno == 1060:
                pass
            else:
                print(f"⚠️  Error executing {query}: {err}")
    conn.commit()

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
