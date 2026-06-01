"""
Real-Time Transaction Simulator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Streams one random transaction every 2 seconds to:
  POST http://localhost:5000/api/transactions/predict

Rules
  • 10 % of transactions are obviously fraudulent
      → amount > 40 000, hour between 1-4 am
  • Remaining 90 % are normal legitimate transactions

Terminal output
  GREEN  = legitimate
  RED    = fraud detected

Runs for 60 seconds then prints a summary.

Usage:
  python simulation/live_simulator.py
"""

import random
import time
import json
from datetime import datetime

import requests
from faker import Faker

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

# ── Config ────────────────────────────────────────────────────────────────────
API_URL        = "http://localhost:5000/api/transactions/predict"
INTERVAL_SEC   = 2          # seconds between transactions
DURATION_SEC   = 60         # total run time
FRAUD_RATE     = 0.10       # 10 % forced fraudulent

CATEGORIES = ["utilities", "travel", "entertainment", "food", "online", "healthcare"]

US_CITIES = [
    "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX",
    "Phoenix, AZ", "Philadelphia, PA", "San Antonio, TX", "San Diego, CA",
    "Dallas, TX", "San Jose, CA", "Austin, TX", "Jacksonville, FL",
    "Fort Worth, TX", "Columbus, OH", "Charlotte, NC", "Indianapolis, IN",
    "San Francisco, CA", "Seattle, WA", "Denver, CO", "Nashville, TN",
]

fake = Faker()


# ── Transaction generators ────────────────────────────────────────────────────
def make_legit_transaction() -> dict:
    """Normal, low-risk transaction."""
    return {
        "amount":      round(random.uniform(10, 39_999), 2),
        "hour":        random.randint(6, 22),          # daytime / evening
        "day_of_week": random.randint(0, 6),
        "is_foreign":  0,
        "category":    random.choice(CATEGORIES),
        "merchant":    fake.company(),
        "location":    random.choice(US_CITIES),
    }


def make_fraud_transaction() -> dict:
    """Obvious fraud pattern: very large amount + early-morning hour."""
    return {
        "amount":      round(random.uniform(40_001, 50_000), 2),
        "hour":        random.randint(1, 4),           # 1 – 4 am
        "day_of_week": random.randint(0, 6),
        "is_foreign":  0,
        "category":    random.choice(CATEGORIES),
        "merchant":    fake.company(),
        "location":    random.choice(US_CITIES),
    }


def generate_transaction() -> tuple[dict, bool]:
    """Return (payload, intended_fraud_flag)."""
    is_intended_fraud = random.random() < FRAUD_RATE
    txn = make_fraud_transaction() if is_intended_fraud else make_legit_transaction()
    return txn, is_intended_fraud


# ── Formatting helpers ────────────────────────────────────────────────────────
def _bar(width: int = 40) -> str:
    return "─" * width


def print_header():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{BOLD}{CYAN}{'━'*60}{RESET}")
    print(f"{BOLD}{CYAN}  🔍 Fraud Detection — Live Simulator{RESET}")
    print(f"{CYAN}  API  : {API_URL}{RESET}")
    print(f"{CYAN}  Rate : 1 transaction every {INTERVAL_SEC}s for {DURATION_SEC}s{RESET}")
    print(f"{CYAN}  Start: {now}{RESET}")
    print(f"{BOLD}{CYAN}{'━'*60}{RESET}\n")


def print_result(txn: dict, result: dict, seq: int, intended_fraud: bool):
    """Print a single transaction result with colour."""
    is_fraud     = result.get("is_fraud", False)
    confidence   = result.get("confidence", 0.0)
    risk_level   = result.get("risk_level", "UNKNOWN")
    pct          = f"{confidence * 100:.1f}%"
    ts           = datetime.now().strftime("%H:%M:%S")

    if is_fraud:
        colour  = RED
        icon    = "🚨"
        verdict = "FRAUD DETECTED"
    else:
        colour  = GREEN
        icon    = "✅"
        verdict = "LEGITIMATE"

    bar = f"{DIM}{_bar(44)}{RESET}"
    print(f"{bar}")
    print(
        f"  {colour}{BOLD}#{seq:>3}  {icon}  {verdict}{RESET}"
        f"   {DIM}{ts}{RESET}"
    )
    print(
        f"       {DIM}Amount :{RESET} ${txn['amount']:>10,.2f}   "
        f"{DIM}Hour:{RESET} {txn['hour']:02d}:00   "
        f"{DIM}Day:{RESET} {txn['day_of_week']}"
    )
    print(
        f"       {DIM}Category:{RESET} {txn['category']:<14}  "
        f"{DIM}Location:{RESET} {txn['location']}"
    )
    print(
        f"       {DIM}Merchant:{RESET} {txn['merchant'][:30]}"
    )
    print(
        f"       {colour}Confidence: {pct}   Risk: {risk_level}{RESET}"
    )


def print_summary(total: int, fraud_detected: int, errors: int, elapsed: float):
    """Print end-of-run statistics."""
    legit_detected = total - fraud_detected - errors
    accuracy_note  = (
        f"{fraud_detected / total * 100:.1f}% flagged as fraud"
        if total else "N/A"
    )

    print(f"\n{BOLD}{CYAN}{'━'*60}{RESET}")
    print(f"{BOLD}{CYAN}  📊  Simulation Summary{RESET}")
    print(f"{CYAN}{'─'*60}{RESET}")
    print(f"  Total sent       : {BOLD}{total}{RESET}")
    print(f"  {GREEN}Legit detected  : {legit_detected}{RESET}")
    print(f"  {RED}Fraud detected  : {fraud_detected}{RESET}")
    print(f"  Errors           : {errors}")
    print(f"  Elapsed          : {elapsed:.1f}s")
    print(f"  Fraud flag rate  : {accuracy_note}")
    print(f"{BOLD}{CYAN}{'━'*60}{RESET}\n")


# ── Main loop ─────────────────────────────────────────────────────────────────
def run():
    print_header()

    total_sent     = 0
    fraud_detected = 0
    errors         = 0
    start_time     = time.time()
    end_time       = start_time + DURATION_SEC

    while time.time() < end_time:
        txn, intended_fraud = generate_transaction()
        total_sent += 1

        # Build API payload (only fields the endpoint expects)
        payload = {
            "amount":      txn["amount"],
            "hour":        txn["hour"],
            "day_of_week": txn["day_of_week"],
            "is_foreign":  txn["is_foreign"],
            "category":    txn["category"],
        }

        try:
            resp   = requests.post(
                API_URL,
                json=payload,
                timeout=5,
                headers={"Content-Type": "application/json"},
            )
            result = resp.json()

            if resp.status_code != 200:
                raise ValueError(result.get("error", f"HTTP {resp.status_code}"))

            if result.get("is_fraud"):
                fraud_detected += 1

            print_result(txn, result, total_sent, intended_fraud)

        except requests.exceptions.ConnectionError:
            errors += 1
            print(f"  {RED}#{total_sent:>3}  ❌  Connection refused — is the Flask API running?{RESET}")
        except requests.exceptions.Timeout:
            errors += 1
            print(f"  {RED}#{total_sent:>3}  ⏱  Request timed out{RESET}")
        except Exception as exc:
            errors += 1
            print(f"  {RED}#{total_sent:>3}  ⚠  Error: {exc}{RESET}")

        # Remaining time display
        remaining = max(0, end_time - time.time())
        print(f"  {DIM}⏳ {remaining:.0f}s remaining…{RESET}")

        time.sleep(INTERVAL_SEC)

    elapsed = time.time() - start_time
    print_summary(total_sent, fraud_detected, errors, elapsed)


if __name__ == "__main__":
    run()
