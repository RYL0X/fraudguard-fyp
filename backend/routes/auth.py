"""
Authentication blueprint — /api/auth
Provides login, logout, and profile endpoints using JWT.
"""
import os
import jwt
import datetime
from functools import wraps
from flask import Blueprint, request, jsonify
import json
import threading

auth_bp = Blueprint('auth', __name__)

# ── Secret key (override via JWT_SECRET env var)
JWT_SECRET  = os.getenv('JWT_SECRET', 'fraudguard-super-secret-2024')
JWT_ALGO    = 'HS256'
JWT_EXPIRY  = datetime.timedelta(hours=8)

# ── Auth Data Persistence
STORE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'auth_store.json')

# Reentrant lock to prevent concurrent write/read corruption and race conditions
store_lock = threading.RLock()

def load_store():
    default_state = {
        'USERS': {
            'admin@fraudguard.com': {
                'password':    'admin123',
                'name':        'Chief Analyst',
                'role':        'Administrator',
                'last_login':  None,
                'permissions': ['read', 'write', 'admin', 'export'],
            }
        },
        'ACTIVITY_LOGS': [
            {
                'timestamp': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
                'user': 'system',
                'action': 'System startup',
                'details': 'FraudGuard API initialized.'
            }
        ]
    }
    with store_lock:
        if os.path.exists(STORE_PATH):
            try:
                with open(STORE_PATH, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and 'USERS' in data and 'ACTIVITY_LOGS' in data:
                        return data
                    else:
                        print("Warning: Invalid structure in auth_store.json. Using default initial state.")
            except Exception as e:
                print("Error loading auth_store.json:", e)
        return default_state

def save_store(store_data):
    with store_lock:
        try:
            os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
            with open(STORE_PATH, 'w') as f:
                json.dump(store_data, f, indent=4)
        except Exception as e:
            print("Error saving auth_store.json:", e)

store = load_store()
USERS = store['USERS']
ACTIVITY_LOGS = store['ACTIVITY_LOGS']

def _log_activity(email: str, action: str, details: str = ""):
    with store_lock:
        ACTIVITY_LOGS.insert(0, {
            'timestamp': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
            'user': email,
            'action': action,
            'details': details
        })
        # Prevent logs from growing infinitely in memory and disk
        if len(ACTIVITY_LOGS) > 500:
            del ACTIVITY_LOGS[500:]
        save_store({'USERS': USERS, 'ACTIVITY_LOGS': ACTIVITY_LOGS})




# ── Helper: generate token
def _generate_token(email: str) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        'sub': email,
        'iat': now,
        'exp': now + JWT_EXPIRY,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
    if isinstance(token, bytes):
        return token.decode('utf-8')
    return token


# ── Helper: decode token
def _decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except (jwt.PyJWTError, ValueError, TypeError):
        return None


# ── Decorator: require valid JWT
def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
        
        parts = auth_header.split(' ', 1)
        if len(parts) != 2:
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
            
        token = parts[1].strip()
        if not token:
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
            
        payload = _decode_token(token)
        if payload is None:
            return jsonify({'error': 'Token expired or invalid. Please log in again.'}), 401
        request.current_user = payload.get('sub')
        return f(*args, **kwargs)
    return decorated


# ══════════════════════════════════════════════════════════════
# POST /api/auth/login
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/login', methods=['POST'])
def login():
    """Accept {email, password} and return a JWT on success."""
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    password = data.get('password')

    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({'error': 'Email and password must be strings'}), 400

    email = email.strip().lower()
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    with store_lock:
        user = USERS.get(email)
        if not user or user.get('password') != password:
            return jsonify({'error': 'Invalid email or password'}), 401

        # Update last login timestamp
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        user['last_login'] = now_str
        
        _log_activity(email, 'Login', 'User authenticated successfully.')

    token = _generate_token(email)

    return jsonify({
        'token': token,
        'user': {
            'name':       user.get('name'),
            'email':      email,
            'role':       user.get('role'),
            'last_login': now_str,
        }
    }), 200


# ══════════════════════════════════════════════════════════════
# GET /api/auth/logout
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/logout', methods=['GET'])
def logout():
    """Client should discard its token. Server-side: stateless acknowledgement."""
    return jsonify({'message': 'Logged out successfully'}), 200


# ══════════════════════════════════════════════════════════════
# GET /api/auth/profile
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/profile', methods=['GET'])
@jwt_required
def profile():
    """Return current user info decoded from the JWT."""
    email = request.current_user
    with store_lock:
        user = USERS.get(email)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'name':        user.get('name'),
        'email':       email,
        'role':        user.get('role'),
        'last_login':  user.get('last_login'),
        'permissions': user.get('permissions', []),
    }), 200


# ══════════════════════════════════════════════════════════════
# POST /api/auth/change_password
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/change_password', methods=['POST'])
@jwt_required
def change_password():
    email = request.current_user
    
    data = request.get_json(silent=True) or {}
    current_pw = data.get('current_password')
    new_pw = data.get('new_password')
    
    if not isinstance(current_pw, str) or not isinstance(new_pw, str):
        return jsonify({'error': 'Current and new passwords must be strings'}), 400
        
    if not current_pw or not new_pw:
        return jsonify({'error': 'Current and new passwords are required'}), 400
        
    with store_lock:
        user = USERS.get(email)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        if user.get('password') != current_pw:
            return jsonify({'error': 'Incorrect current password'}), 401
            
        user['password'] = new_pw
        _log_activity(email, 'Password Change', 'User updated their password.')
    
    return jsonify({'message': 'Password updated successfully'}), 200


# ══════════════════════════════════════════════════════════════
# GET /api/auth/activity
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/activity', methods=['GET'])
@jwt_required
def get_activity():
    email = request.current_user
    with store_lock:
        # Return last 20 activities for the user
        user_logs = [
            log for log in ACTIVITY_LOGS 
            if isinstance(log, dict) and (log.get('user') == email or log.get('user') == 'system')
        ]
    return jsonify(user_logs[:20]), 200
