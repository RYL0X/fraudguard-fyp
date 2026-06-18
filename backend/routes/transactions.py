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
    import uuid
    import datetime

    data = request.get_json(silent=True) or {}
    required = ['amount', 'hour', 'day_of_week', 'category', 'merchant', 'location']
    missing  = [f for f in required if f not in data]
    if missing:
        return jsonify({'error': f'Missing fields: {missing}'}), 400

    try:
        # 1. Normalize Day of Week
        dow_raw = data.get('day_of_week')
        if isinstance(dow_raw, str):
            dow_map = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            dow = dow_map.get(dow_raw.lower(), 0)
        else:
            dow = int(dow_raw)
            
        # 2. Normalize Category
        cat_raw = data.get('category', '')
        cat_lower = cat_raw.lower()
        if "retail" in cat_lower or "e-commerce" in cat_lower:
            cat_norm = "online"
        elif "food" in cat_lower or "dining" in cat_lower:
            cat_norm = "food"
        elif "travel" in cat_lower:
            cat_norm = "travel"
        elif "entertainment" in cat_lower:
            cat_norm = "entertainment"
        elif "healthcare" in cat_lower:
            cat_norm = "healthcare"
        elif "utilities" in cat_lower:
            cat_norm = "utilities"
        else:
            cat_norm = cat_lower.replace(" ", "_")
            
        # 3. Infer is_foreign
        location = data.get('location', '')
        local_cities = ["pakistan", "faisalabad", "lahore", "karachi", "islamabad", "rawalpindi", "multan"]
        is_foreign = 1
        if any(city in location.lower() for city in local_cities):
            is_foreign = 0
            
        amount = float(data.get('amount', 0))
        hour = int(data.get('hour', 0))
        merchant = data.get('merchant', 'Unknown')
        
        # Prepare payload for ML
        ml_data = {
            'amount': amount,
            'hour': hour,
            'day_of_week': dow,
            'is_foreign': is_foreign,
            'category': cat_norm
        }

        result = predict(ml_data)

        now = datetime.datetime.now()
        is_fraud = result.get('is_fraud', False)
        confidence = float(result.get('confidence', 0.0))
        risk_level = result.get('risk_level', 'LOW')
        decision = 'declined' if is_fraud else 'approved'
        risk_score = confidence
        
        message = "Transaction processed normally."
        if is_fraud or risk_level == 'HIGH' or confidence >= 0.70:
            message = "High risk transaction flagged by ML model."
            
        txn_id = str(uuid.uuid4())
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Insert Transaction
        cursor.execute("""
            INSERT INTO transactions
            (id, user_id, amount, merchant, category, location, timestamp, 
             is_foreign, hour, day_of_week, is_fraud, confidence, risk_level, source, decision)
            VALUES (%s, 1, %s, %s, %s, %s, NOW(), %s, %s, %s, %s, %s, %s, 'predict', %s)
        """, (txn_id, amount, merchant, cat_norm, location, is_foreign, hour, dow, int(is_fraud), confidence, risk_level, decision))
        
        # Insert Alert if conditions met
        alert_created = False
        if is_fraud or risk_level == 'HIGH' or confidence >= 0.70:
            alert_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO alerts
                (id, transaction_id, amount, merchant, category, location, risk_score, risk_level, status, source, message, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'new', 'predict', %s, NOW())
            """, (alert_id, txn_id, amount, merchant, cat_norm, location, confidence, risk_level, message))
            alert_created = True
            
        conn.commit()
        cursor.close()
        conn.close()

        from backend.app import socketio

        socketio.emit('new_transaction', {
            'id': txn_id,
            'amount': amount,
            'merchant': merchant,
            'is_fraud': is_fraud,
            'risk_level': risk_level,
            'confidence': confidence,
            'timestamp': str(now)
        })

        if alert_created:
            socketio.emit('new_alert', {
                'transaction_id': txn_id,
                'amount': amount,
                'merchant': merchant,
                'risk_level': risk_level,
                'risk_score': confidence,
                'timestamp': str(now)
            })

        _maybe_alert(ml_data, result)
        
        # Return response
        return jsonify({
            'transaction_id': txn_id,
            'is_fraud': is_fraud,
            'decision': decision,
            'confidence': confidence,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'message': message
        })
    except FileNotFoundError as exc:
        return jsonify({'error': str(exc)}), 503
    except Exception as exc:
        return jsonify({'error': f'Prediction failed: {exc}'}), 500


# ── POST /api/external/transaction ────────────────────────────────────────
external_bp = Blueprint('external', __name__)

@external_bp.route('/transaction', methods=['POST'])
def external_transaction():
    """
    Receives transactions from external apps (e.g. SecurePay dummy app),
    runs them through the real ML model, saves to DB, fires alerts & emails.
    """
    import uuid
    import datetime
    import logging

    logger = logging.getLogger(__name__)
    data = request.get_json(silent=True) or {}

    # ── 1. Validate required fields ───────────────────────────────────
    required = ['customer_name', 'customer_email', 'amount', 'merchant', 'category', 'location']
    missing  = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing required fields: {missing}'}), 400

    try:
        now = datetime.datetime.now()

        # ── 2. Normalise inputs ───────────────────────────────────────
        amount         = float(data['amount'])
        merchant       = str(data['merchant']).strip()
        location       = str(data['location']).strip()
        customer_name  = str(data['customer_name']).strip()
        customer_email = str(data['customer_email']).strip()
        card_last4     = str(data.get('card_last4', '')).strip() or None
        source         = str(data.get('source', 'dummy_app')).strip()

        # hour / day_of_week
        hour        = int(data['hour'])        if 'hour'        in data else now.hour
        day_of_week = int(data['day_of_week']) if 'day_of_week' in data else now.weekday()

        # is_foreign: explicit or infer from location
        if 'is_foreign' in data:
            is_foreign = int(bool(data['is_foreign']))
        else:
            local_kw = ['pakistan', 'faisalabad', 'lahore', 'karachi',
                        'islamabad', 'rawalpindi', 'multan']
            is_foreign = 0 if any(k in location.lower() for k in local_kw) else 1

        # category normalisation (same map as /predict)
        cat_raw   = str(data['category']).lower().strip()
        cat_map   = {
            'retail': 'online', 'e-commerce': 'online', 'online': 'online',
            'food': 'food', 'dining': 'food',
            'travel': 'travel',
            'entertainment': 'entertainment',
            'healthcare': 'healthcare',
            'utilities': 'utilities',
            'electronics': 'electronics',
            'education': 'education',
            'fuel': 'fuel',
            'clothing': 'clothing',
        }
        cat_norm = cat_map.get(cat_raw, cat_raw.replace(' ', '_'))

        # ── 3. Run ML prediction ──────────────────────────────────────
        ml_data = {
            'amount':      amount,
            'hour':        hour,
            'day_of_week': day_of_week,
            'is_foreign':  is_foreign,
            'category':    cat_norm,
        }
        result     = predict(ml_data)
        is_fraud   = bool(result.get('is_fraud', False))
        confidence = float(result.get('confidence', 0.0))
        risk_level = result.get('risk_level', 'LOW')

        # Decision
        if is_fraud or risk_level in ('HIGH', 'FRAUD'):
            decision       = 'blocked'
            status         = 'blocked'
        elif confidence >= 0.70:
            decision       = 'under_review'
            status         = 'under_review'
        else:
            decision       = 'approved'
            status         = 'approved'

        message = (
            'High risk transaction detected from SecurePay dummy transaction app.'
            if status != 'approved'
            else 'Transaction processed and approved.'
        )

        txn_id = str(uuid.uuid4())

        # ── 4. Save transaction ───────────────────────────────────────
        conn   = get_connection()
        cursor = conn.cursor()

        # Try with card_last4 / customer columns; fall back gracefully
        try:
            cursor.execute("""
                INSERT INTO transactions
                (id, user_id, amount, merchant, category, location, timestamp,
                 is_foreign, hour, day_of_week, is_fraud, confidence, risk_level,
                 source, decision, customer_name, customer_email, card_last4)
                VALUES (%s, 1, %s, %s, %s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (txn_id, amount, merchant, cat_norm, location,
                  is_foreign, hour, day_of_week,
                  int(is_fraud), confidence, risk_level,
                  source, decision, customer_name, customer_email, card_last4))
        except Exception:
            # Fallback without extra columns
            cursor.execute("""
                INSERT INTO transactions
                (id, user_id, amount, merchant, category, location, timestamp,
                 is_foreign, hour, day_of_week, is_fraud, confidence, risk_level,
                 source, decision)
                VALUES (%s, 1, %s, %s, %s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s)
            """, (txn_id, amount, merchant, cat_norm, location,
                  is_foreign, hour, day_of_week,
                  int(is_fraud), confidence, risk_level,
                  source, decision))

        # ── 5. Create alert if high-risk ──────────────────────────────
        alert_created = False
        if is_fraud or risk_level in ('HIGH', 'FRAUD') or confidence >= 0.70:
            alert_id = str(uuid.uuid4())
            try:
                cursor.execute("""
                    INSERT INTO alerts
                    (id, transaction_id, amount, merchant, category, location,
                     risk_score, risk_level, status, source, message, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'new', %s, %s, NOW())
                """, (alert_id, txn_id, amount, merchant, cat_norm, location,
                      confidence, risk_level, source, message))
                alert_created = True
            except Exception as ae:
                logger.warning('Alert insert failed: %s', ae)

        conn.commit()
        cursor.close()
        conn.close()

        # ── 6. Send customer email ────────────────────────────────────
        if alert_created and customer_email and _NOTIFICATIONS_ENABLED:
            def _send_customer_email():
                try:
                    from backend.notifications import send_email
                    send_email(customer_email, {
                        'amount':     amount,
                        'merchant':   merchant,
                        'location':   location,
                        'risk_level': risk_level,
                        'confidence': confidence,
                        'is_fraud':   is_fraud,
                        'timestamp':  now.strftime('%Y-%m-%d %H:%M:%S'),
                    })
                except Exception as ex:
                    logger.warning('Customer email failed: %s', ex)

            import threading
            threading.Thread(target=_send_customer_email, daemon=True).start()

        # ── 7. Emit Socket.IO events ──────────────────────────────────
        try:
            from backend.app import socketio
            socketio.emit('new_transaction', {
                'id':          txn_id,
                'amount':      amount,
                'merchant':    merchant,
                'category':    cat_norm,
                'location':    location,
                'is_fraud':    is_fraud,
                'confidence':  confidence,
                'risk_level':  risk_level,
                'source':      source,
                'timestamp':   str(now),
            })
            if alert_created:
                socketio.emit('new_alert', {
                    'transaction_id': txn_id,
                    'amount':         amount,
                    'merchant':       merchant,
                    'risk_level':     risk_level,
                    'risk_score':     confidence,
                    'source':         source,
                    'timestamp':      str(now),
                })
        except Exception as se:
            logger.warning('Socket emit failed: %s', se)

        # ── 8. Return response ────────────────────────────────────────
        return jsonify({
            'transaction_id': txn_id,
            'status':         status,
            'decision':       decision,
            'is_fraud':       is_fraud,
            'confidence':     confidence,
            'risk_level':     risk_level,
            'message':        message,
            'alert_created':  alert_created,
        })

    except FileNotFoundError as exc:
        return jsonify({'error': str(exc)}), 503
    except Exception as exc:
        return jsonify({'error': f'Transaction processing failed: {exc}'}), 500
