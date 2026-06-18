"""
Flask application factory.
Run from project root: python run.py
"""
import os
import sys

# Ensure the project root is always importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, redirect, send_file, send_from_directory, url_for
from flask_cors import CORS
from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)
    socketio.init_app(app)

    # ── API blueprints
    from backend.routes.transactions import transactions_bp, external_bp
    from backend.routes.stats        import stats_bp
    from backend.routes.auth         import auth_bp
    from backend.routes.alerts       import alerts_bp

    app.register_blueprint(transactions_bp, url_prefix='/api/transactions')
    app.register_blueprint(external_bp,     url_prefix='/api/external')
    app.register_blueprint(stats_bp,        url_prefix='/api/stats')
    app.register_blueprint(auth_bp,         url_prefix='/api/auth')
    app.register_blueprint(alerts_bp,       url_prefix='/api/alerts')

    # ── Health check
    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok', 'message': 'Fraud Detection API is running ✅'})

    # ── Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Endpoint not found'}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Internal server error'}), 500

    # ── Root → redirect to login
    @app.route('/')
    def index():
        return redirect('/login')

    # ── Login page
    @app.route('/login')
    def login_page():
        return send_file(
            os.path.join(os.path.dirname(__file__), '..', 'frontend', 'login.html')
        )

    # ── Dashboard (protected client-side via JWT check in index.html)
    @app.route('/dashboard')
    def dashboard():
        return send_file(
            os.path.join(os.path.dirname(__file__), '..', 'frontend', 'index.html')
        )

    # ── Serve any other frontend static files
    @app.route('/frontend/<path:filename>')
    def frontend_files(filename):
        return send_from_directory(
            os.path.join(os.path.dirname(__file__), '..', 'frontend'), filename
        )

    # ── SecurePay Dummy Transaction App ──────────────────────────────
    @app.route('/pay')
    def payment_app():
        return send_file(
            os.path.join(
                os.path.dirname(__file__), '..', 'dummy_transaction_app', 'index.html'
            )
        )

    @app.route('/dummy_transaction_app/<path:filename>')
    def dummy_app_static(filename):
        return send_from_directory(
            os.path.join(os.path.dirname(__file__), '..', 'dummy_transaction_app'),
            filename
        )

    @app.route('/api/test-email')
    def test_email():
        try:
            from backend.notifications import send_email
            import os

            recipient = os.getenv("ALERT_EMAIL") or os.getenv("GMAIL_USER")

            if not recipient:
                return jsonify({
                    "success": False,
                    "error": "ALERT_EMAIL and GMAIL_USER are missing"
                }), 500

            result = send_email(recipient, {
                "amount": 999,
                "merchant": "Render Email Test",
                "location": "Render",
                "risk_level": "HIGH",
                "confidence": 99,
                "decision": "blocked",
                "timestamp": "Render test"
            })

            return jsonify({
                "success": True,
                "message": "test email endpoint executed",
                "result": str(result)
            })

        except Exception as e:
            print("EMAIL TEST ERROR:", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('FLASK_PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)

