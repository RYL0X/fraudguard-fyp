from ml_model.predict import predict
import time

def test_fraud_detection():
    result = predict({
        'amount': 45000, 
        'hour': 2, 
        'day_of_week': 0,
        'category': 'online',
        'is_foreign': 1
    })
    assert result['is_fraud'] == True

def test_legit_detection():
    result = predict({
        'amount': 50, 
        'hour': 14, 
        'day_of_week': 2,
        'category': 'food',
        'is_foreign': 0
    })
    assert result['is_fraud'] == False

def test_confidence_range():
    result = predict({
        'amount': 1000, 
        'hour': 10,
        'day_of_week': 1,
        'category': 'retail',
        'is_foreign': 0
    })
    assert 0 <= result['confidence'] <= 1.0

def test_risk_level_valid():
    result = predict({
        'amount': 5000, 
        'hour': 8,
        'day_of_week': 3,
        'category': 'travel',
        'is_foreign': 0
    })
    assert result['risk_level'] in [
        'LOW', 'MEDIUM', 'HIGH'
    ]

def test_prediction_speed():
    start = time.time()
    predict({
        'amount': 2000, 
        'hour': 12,
        'day_of_week': 2,
        'category': 'food',
        'is_foreign': 0
    })
    end = time.time()
    assert (end - start) < 1.0