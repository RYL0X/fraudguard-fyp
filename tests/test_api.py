import pytest
import sys
import os
sys.path.insert(0, 
    os.path.dirname(os.path.dirname(__file__)))
from backend.app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_predict_valid(client):
    response = client.post(
        '/api/transactions/predict',
        json={
            'amount': 45000,
            'hour': 2,
            'day_of_week': 0,
            'category': 'online',
            'merchant': 'Test Shop',
            'location': 'Karachi',
            'is_foreign': 1
        }
    )
    assert response.status_code == 200

def test_predict_has_keys(client):
    response = client.post(
        '/api/transactions/predict',
        json={
            'amount': 1000,
            'hour': 10,
            'day_of_week': 1,
            'category': 'food',
            'merchant': 'ABC Store',
            'location': 'Lahore',
            'is_foreign': 0
        }
    )
    data = response.get_json()
    assert 'is_fraud' in data
    assert 'confidence' in data
    assert 'risk_level' in data

def test_predict_missing_fields(client):
    response = client.post(
        '/api/transactions/predict',
        json={'amount': 1000}
    )
    assert response.status_code == 400

def test_get_transactions(client):
    response = client.get(
        '/api/transactions/',
        follow_redirects=True
    )
    assert response.status_code == 200

def test_get_stats(client):
    response = client.get(
        '/api/stats/summary',
        follow_redirects=True
    )
    data = response.get_json()
    assert response.status_code == 200
    assert 'total_transactions' in data