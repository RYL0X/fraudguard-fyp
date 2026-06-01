"""
/api/transactions  — paginated list, single lookup, fraud prediction.
"""
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from flask import Blueprint, request, jsonify
from backend.db import get_connection
from ml_model.predict import predict

# Notifications import is wrapped in a try/except so the rest of the app
# keeps working even if python-dotenv or smtplib is misconfigured.
try:
    from backend.notifications import send_alert as _send_alert
    _NOTIFICATIONS_ENABLED = True
except Exception as _notif_import_err:
    _NOTIFICATIONS_ENABLED = False
    import logging
    logging.getLogger(__name__).warning(
        "Notifications disabled — import error: %s", _notif_import_err
    )

transactions_bp = Blueprint('transactions', __name__)


def _serialize(row: dict) -> dict:
    """Convert MySQL types to JSON-safe types."""
    if row.get('timestamp') and hasattr(row['timestamp'], 'strftime'):
        row['timestamp'] = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    row['amount']     = float(row['amount'])     if row.get('amount')     is not None else None
    row['confidence'] = float(row['confidence']) if row.get('confidence') is not None else None
    return row


def _maybe_alert(payload: dict, result: dict):
    """
    Fire send_alert() in a daemon thread when a prediction is HIGH risk
    or flagged as fraud.  Never blocks the HTTP response.
    """
    if not _NOTIFICATIONS_ENABLED:
        return
    if not (result.get('is_fraud') or result.get('risk_level') == 'HIGH'):
        return

    # Merge request data + prediction result into a single alert payload
    alert_data = {
        'amount':     payload.get('amount'),
        'merchant':   payload.get('merchant', 'Unknown'),
        'location':   payload.get('location', 'Unknown'),
        'category':   payload.get('category', 'Unknown'),
        'risk_level': result.get('risk_level', 'HIGH'),
        'confidence': result.get('confidence', 0),
        'is_fraud':   result.get('is_fraud', True),
        'timestamp':  payload.get('timestamp',
                      __import__('datetime').datetime.now()
                      .strftime('%Y-%m-%d %H:%M:%S')),
    }

    thread = threading.Thread(target=_send_alert, args=(alert_data,), daemon=True)
    thread.start()


# ── GET /api/transactions ──────────────────────────────────────────────────
@transactions_bp.route('/', methods=['GET'])
def get_transactions():
    page       = max(1, int(request.args.get('page', 1)))
    per_page   = min(100, int(request.args.get('per_page', 20)))
    search     = request.args.get('search', '').strip()
    fraud_only = request.args.get('fraud', '')
    offset     = (page - 1) * per_page

    where, params = [], []
    if search:
        where.append("(id LIKE %s OR CAST(user_id AS CHAR) LIKE %s OR merchant LIKE %s OR location LIKE %s OR category LIKE %s)")
        params += [f'%{search}%'] * 5
    if fraud_only == 'true':
        where.append("is_fraud = 1")
    elif fraud_only == 'false':
        where.append("is_fraud = 0")

    w = ("WHERE " + " AND ".join(where)) if where else ""

    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(f"SELECT COUNT(*) AS total FROM transactions {w}", params)
    total = cursor.fetchone()['total']

    cursor.execute(
        f"SELECT * FROM transactions {w} ORDER BY timestamp DESC LIMIT %s OFFSET %s",
        params + [per_page, offset],
    )
    rows = [_serialize(r) for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    return jsonify({
        'data':     rows,
        'total':    total,
        'page':     page,
        'per_page': per_page,
        'pages':    max(1, (total + per_page - 1) // per_page),
    })


# ── GET /api/transactions/<id> ─────────────────────────────────────────────
@transactions_bp.route('/<string:txn_id>', methods=['GET'])
def get_transaction(txn_id):
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM transactions WHERE id = %s", (txn_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return jsonify({'error': 'Transaction not found'}), 404
    return jsonify(_serialize(row))


# ── POST /api/transactions/predict ────────────────────────────────────────
@transactions_bp.route('/predict', methods=['POST'])
def predict_transaction():
    data     = request.get_json(silent=True) or {}
    required = ['amount', 'hour', 'day_of_week', 'is_foreign', 'category']
    missing  = [f for f in required if f not in data]
    if missing:
        return jsonify({'error': f'Missing fields: {missing}'}), 400

    try:
        result = predict(data)

        # ── Fire fraud alert (non-blocking) ──────────────────────────────
        _maybe_alert(data, result)
        # ─────────────────────────────────────────────────────────────────

        return jsonify(result)
    except FileNotFoundError as exc:
        return jsonify({'error': str(exc)}), 503
    except Exception as exc:
        return jsonify({'error': f'Prediction failed: {exc}'}), 500
