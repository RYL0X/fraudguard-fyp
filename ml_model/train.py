"""
Train a RandomForestClassifier on the generated transaction dataset.
Usage (from project root): python ml_model/train.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score

BASE      = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE, '..', 'data', 'transactions.csv')
MODEL_PATH   = os.path.join(BASE, 'fraud_model.pkl')
ENCODER_PATH = os.path.join(BASE, 'label_encoder.pkl')

FEATURES = ['amount', 'hour', 'day_of_week', 'is_foreign', 'category_encoded']


def train():
    print("📂 Loading data …")
    df = pd.read_csv(DATA_PATH)
    print(f"   {len(df):,} rows  |  fraud rate: {df['is_fraud'].mean():.1%}")

    le = LabelEncoder()
    df['category_encoded'] = le.fit_transform(df['category'])

    X = df[FEATURES]
    y = df['is_fraud']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("🌲 Training RandomForestClassifier …")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight='balanced',
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    print("\n=== Classification Report ===")
    print(classification_report(y_test, y_pred, target_names=['Legit', 'Fraud']))
    print("=== Confusion Matrix ===")
    print(confusion_matrix(y_test, y_pred))
    print(f"ROC-AUC: {roc_auc_score(y_test, y_prob):.4f}\n")

    joblib.dump(model, MODEL_PATH)
    joblib.dump(le,    ENCODER_PATH)
    print(f"✅ Model saved   → {MODEL_PATH}")
    print(f"✅ Encoder saved → {ENCODER_PATH}")


if __name__ == '__main__':
    train()
