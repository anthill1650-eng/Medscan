import subprocess
import sys
import time
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).parent
PORT = 8001
URL = f"http://127.0.0.1:{PORT}/"

def start_backend():
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "api:app",
        "--host", "127.0.0.1",
        "--port", str(PORT),
    ]
    return subprocess.Popen(cmd, cwd=str(BASE_DIR))

if __name__ == "__main__":
    proc = start_backend()
    time.sleep(2.5)
    webbrowser.open(URL)
    proc.wait()
