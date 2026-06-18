"""
Project entry point.
Usage: python run.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import create_app, socketio

if __name__ == '__main__':
    app  = create_app()
    port = int(os.getenv('FLASK_PORT', 5000))
    print(f"Server starting on http://localhost:{port}")
    socketio.run(app, debug=True, host='0.0.0.0', port=port)
