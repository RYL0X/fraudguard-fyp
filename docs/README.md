# Fraud Detection System

A full-stack ML-powered fraud detection application built with Flask, scikit-learn, MySQL, and a vanilla HTML/CSS/JS dashboard.

---

## Project Structure

```
fraud_detection/
├── run.py                    # Start the API server
├── requirements.txt
├── .env.example              # Copy to .env and fill credentials
├── backend/
│   ├── app.py                # Flask application factory
│   ├── db.py                 # MySQL connection helper
│   ├── setup_db.py           # One-time DB setup + CSV import
│   └── routes/
│       ├── transactions.py   # GET /api/transactions, POST /predict
│       └── stats.py          # GET /api/stats/summary|trend|categories
├── frontend/
│   ├── index.html            # Dashboard SPA
│   ├── style.css             # Dark-mode design system
│   └── app.js                # Chart.js + fetch logic
├── ml_model/
│   ├── train.py              # Train & save the model
│   └── predict.py            # Inference module
├── simulation/
│   └── generate_data.py      # Synthetic data generator (10 k rows)
├── tests/
│   ├── conftest.py
│   ├── test_model.py
│   └── test_api.py
└── docs/
    └── README.md             # ← you are here
```

---

## Quick Start

### 1 — Install dependencies
```bash
pip install -r requirements.txt
```

### 2 — Configure environment
```bash
copy .env.example .env        # Windows
# Edit .env with your MySQL credentials
```

### 3 — Generate synthetic data
```bash
python simulation/generate_data.py
```

### 4 — Train the ML model
```bash
python ml_model/train.py
```

### 5 — Set up the database & load data
```bash
python backend/setup_db.py
```

### 6 — Start the API server
```bash
python run.py
# API available at http://localhost:5000
```

### 7 — Open the dashboard
Open `frontend/index.html` in your browser.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/health` | Health check |
| `GET`  | `/api/transactions/` | Paginated transactions (search, fraud filter) |
| `GET`  | `/api/transactions/<id>` | Single transaction |
| `POST` | `/api/transactions/predict` | Predict fraud on a new transaction |
| `GET`  | `/api/stats/summary` | KPI summary |
| `GET`  | `/api/stats/trend` | 30-day daily fraud trend |
| `GET`  | `/api/stats/categories` | Per-category fraud breakdown |

### Predict payload example
```json
{
  "amount": 4500.00,
  "hour": 2,
  "day_of_week": 6,
  "is_foreign": 1,
  "category": "travel"
}
```

---

## Running Tests
```bash
pytest tests/ -v
```

---

## ML Model

- **Algorithm**: `RandomForestClassifier` (100 trees, balanced class weights)
- **Features**: `amount`, `hour`, `day_of_week`, `is_foreign`, `category`
- **Fraud patterns** used in training: large amounts (>$500), micro card-test amounts (<$1), late-night hours (0–5 AM), foreign locations
- **Output**: `is_fraud` (bool), `confidence` (0–1), `risk_level` (LOW / MEDIUM / HIGH)

## Overview
Real-time credit card fraud detection system 
using Machine Learning (RandomForest) with 
95%+ accuracy.

## Tech Stack
- Python Flask (Backend API)
- HTML/CSS/JavaScript (Frontend)
- MySQL (Database)
- scikit-learn RandomForest (ML Model)
- Gmail SMTP (Email Notifications)

## Features
- Real-time fraud detection
- Live admin dashboard
- Automated email alerts
- Transaction simulation
- 10/10 tests passing

## Quick Start
1. pip install -r requirements.txt
2. python simulation/generate_data.py
3. python ml_model/train.py
4. python backend/setup_db.py
5. python run.py

Open: http://localhost:5000/dashboard

## API Endpoints
- POST /api/transactions/predict
- GET /api/transactions/
- GET /api/stats/summary
- GET /api/stats/trend
- GET /api/stats/categories

## Test Results
- 5/5 Model tests passed
- 5/5 API tests passed

## Author
Saad Asim | Government College University Faisalabad | 2026
