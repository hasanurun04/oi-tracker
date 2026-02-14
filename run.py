"""
Uygulamayı başlatmak için:
    python -m uvicorn backend.main:app --reload --port 8000
    python run.py
"""
import subprocess
import sys
import webbrowser
import time
import threading


def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")


if __name__ == "__main__":
    print("=" * 45)
    print("  OI / Supply Tracker başlatılıyor...")
    print("  http://localhost:8000")
    print("  Durdurmak için: Ctrl+C")
    print("=" * 45)

    threading.Thread(target=open_browser, daemon=True).start()

    subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--reload",
        ]
    )
