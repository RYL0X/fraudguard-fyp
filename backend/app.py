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


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    # ── API blueprints
    from backend.routes.transactions import transactions_bp
    from backend.routes.stats        import stats_bp
    from backend.routes.auth         import auth_bp

    app.register_blueprint(transactions_bp, url_prefix='/api/transactions')
    app.register_blueprint(stats_bp,        url_prefix='/api/stats')
    app.register_blueprint(auth_bp,         url_prefix='/api/auth')

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

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('FLASK_PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)

