"""
Inference module — loads the saved model once and exposes predict().
"""
import os
import joblib
import numpy as np

BASE         = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH   = os.path.join(BASE, 'fraud_model.pkl')
ENCODER_PATH = os.path.join(BASE, 'label_encoder.pkl')

_model   = None
_encoder = None


def _load():
    global _model, _encoder
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                "Model not found. Run `python ml_model/train.py` first."
            )
        _model   = joblib.load(MODEL_PATH)
        _encoder = joblib.load(ENCODER_PATH)


def predict(transaction: dict) -> dict:
    """
    Predict fraud for a single transaction.

    Parameters
    ----------
    transaction : dict
        Keys: amount (float), hour (int 0-23), day_of_week (int 0-6),
              is_foreign (int 0/1), category (str)

    Returns
    -------
    dict
        is_fraud (bool), confidence (float 0-1), risk_level (str)
    """
    _load()

    try:
        cat_enc = int(_encoder.transform([transaction['category']])[0])
    except (ValueError, KeyError):
        cat_enc = 0  # unknown category → default

    features = np.array([[
        float(transaction['amount']),
        int(transaction['hour']),
        int(transaction['day_of_week']),
        int(transaction['is_foreign']),
        cat_enc,
    ]])

    prob     = float(_model.predict_proba(features)[0][1])
    is_fraud = prob >= 0.5

    if prob >= 0.70:
        risk = 'HIGH'
    elif prob >= 0.40:
        risk = 'MEDIUM'
    else:
        risk = 'LOW'

    return {
        'is_fraud':   is_fraud,
        'confidence': round(prob, 4),
        'risk_level': risk,
    }
