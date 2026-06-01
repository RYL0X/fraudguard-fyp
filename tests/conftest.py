"""
Shared pytest fixtures for the fraud detection test suite.
"""
import os
import sys
import pytest

# Make the project root importable in all tests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def legit_transaction():
    return {
        'amount':      45.00,
        'hour':        14,
        'day_of_week': 2,
        'is_foreign':  0,
        'category':    'retail',
    }


@pytest.fixture
def fraud_transaction():
    return {
        'amount':      4500.00,
        'hour':        2,
        'day_of_week': 6,
        'is_foreign':  1,
        'category':    'travel',
    }


@pytest.fixture
def app():
    """Return a Flask test client."""
    from backend.app import create_app
    flask_app = create_app()
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client
