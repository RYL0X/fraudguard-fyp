"""
Generates synthetic transaction data with realistic fraud patterns.
Usage: python simulation/generate_data.py
"""
import pandas as pd
import numpy as np
from faker import Faker
import uuid
import os

fake = Faker()
np.random.seed(42)

CATEGORIES    = ['food', 'retail', 'travel', 'entertainment', 'utilities', 'healthcare', 'online']
DOMESTIC_CITIES = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix',
                   'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'San Jose']
FOREIGN_CITIES  = ['London', 'Paris', 'Tokyo', 'Dubai', 'Sydney',
                   'Toronto', 'Berlin', 'Mumbai', 'Singapore', 'Amsterdam']


def generate_transaction(is_fraud: bool = False) -> dict:
    if is_fraud:
        # Fraud patterns: large or micro amounts, odd hours, foreign locations
        if np.random.rand() < 0.7:
            amount = round(np.random.uniform(500, 5000), 2)   # large
        else:
            amount = round(np.random.uniform(0.01, 1.00), 2)  # card-test micro
        hour     = int(np.random.choice(range(0, 6)))          # late-night
        location = np.random.choice(FOREIGN_CITIES if np.random.rand() < 0.6 else DOMESTIC_CITIES)
    else:
        raw    = np.random.lognormal(mean=3.5, sigma=1.0)
        amount = round(float(np.clip(raw, 1.0, 500.0)), 2)
        hour   = int(np.random.choice(range(6, 23)))
        location = np.random.choice(DOMESTIC_CITIES)

    is_foreign = int(location in FOREIGN_CITIES)
    ts = fake.date_time_between(start_date='-1y', end_date='now').replace(hour=hour)

    return {
        'transaction_id': str(uuid.uuid4()),
        'user_id':        int(np.random.randint(1000, 9999)),
        'amount':         amount,
        'merchant':       fake.company(),
        'category':       str(np.random.choice(CATEGORIES)),
        'timestamp':      ts.strftime('%Y-%m-%d %H:%M:%S'),
        'location':       location,
        'is_foreign':     is_foreign,
        'hour':           hour,
        'day_of_week':    ts.weekday(),
        'is_fraud':       int(is_fraud),
    }


def generate_dataset(n: int = 10_000, fraud_rate: float = 0.10) -> pd.DataFrame:
    n_fraud = int(n * fraud_rate)
    n_legit = n - n_fraud

    records = (
        [generate_transaction(is_fraud=False) for _ in range(n_legit)] +
        [generate_transaction(is_fraud=True)  for _ in range(n_fraud)]
    )
    np.random.shuffle(records)

    df = pd.DataFrame(records)

    out = os.path.join(os.path.dirname(__file__), '..', 'data', 'transactions.csv')
    out = os.path.abspath(out)
    df.to_csv(out, index=False)

    print(f"✅ Generated {n:,} transactions  ({n_fraud:,} fraud | {n_legit:,} legit)")
    print(f"   Saved → {out}")
    return df


if __name__ == '__main__':
    generate_dataset(n=10_000, fraud_rate=0.10)
