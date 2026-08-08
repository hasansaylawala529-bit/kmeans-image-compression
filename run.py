"""
Launch the K-Means Image Compression server.
Run: python run.py
"""

import os
import sys
import webbrowser
import threading

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app import app


def open_browser():
    """Open the app in the default browser after a short delay."""
    import time
    time.sleep(1.5)
    webbrowser.open("http://localhost:5000")


if __name__ == "__main__":
    print("\n  K-Means Image Compression")
    print("  -------------------------")
    print("  Server starting at http://localhost:5000")
    print("  Press Ctrl+C to stop\n")

    # Open browser in background
    threading.Thread(target=open_browser, daemon=True).start()

    app.run(debug=False, port=5000, host="0.0.0.0")
