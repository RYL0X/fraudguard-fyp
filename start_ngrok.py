"""
start_ngrok.py  -  Start the Flask backend and expose it via ngrok.

Usage:
    python start_ngrok.py

Requirements:
    - ngrok authtoken must already be saved:
        ngrok config add-authtoken <YOUR_TOKEN>
    - pyngrok must be installed:
        pip install pyngrok
"""

import io
import os
import sys
import time
import threading

# ---------------------------------------------------------------------------
# Force UTF-8 output so emoji / unicode don't crash on Windows cp1252 terminals
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", write_through=True)

# ---------------------------------------------------------------------------
# Make sure the project root is on sys.path
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from pyngrok import ngrok, conf

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PORT = int(os.getenv("FLASK_PORT", 5000))

# ---------------------------------------------------------------------------
# Start Flask in a background thread
# ---------------------------------------------------------------------------
def run_flask():
    from backend.app import create_app
    app = create_app()
    app.run(debug=False, host="0.0.0.0", port=PORT, use_reloader=False)


flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

# Give Flask a moment to bind to the port
time.sleep(2)

# ---------------------------------------------------------------------------
# Open ngrok tunnel
# ---------------------------------------------------------------------------
print(f"\n[ngrok] Opening tunnel to localhost:{PORT} ...")
tunnel = ngrok.connect(PORT, "http")
public_url = tunnel.public_url

print(f"\n{'='*60}")
print(f"  [OK]  Public URL : {public_url}")
print(f"  [TLS] HTTPS URL  : {public_url.replace('http://', 'https://')}")
print(f"  [>>]  Local URL  : http://localhost:{PORT}")
print(f"{'='*60}\n")
print("Press Ctrl+C to stop.\n")

# ---------------------------------------------------------------------------
# Keep the process alive
# ---------------------------------------------------------------------------
try:
    ngrok_process = ngrok.get_ngrok_process()
    ngrok_process.proc.wait()
except KeyboardInterrupt:
    print("\n[ngrok] Shutting down tunnel...")
    ngrok.kill()
    print("[ngrok] Done.")
