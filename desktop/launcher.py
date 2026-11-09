"""OpenShorts desktop launcher (Windows, no Docker).

Starts the FastAPI backend on 127.0.0.1:8000 with the bundled FFmpeg on PATH,
waits until it answers, then opens the dashboard in the default browser.
Run by the Start-menu shortcut as:  python\\pythonw.exe desktop\\launcher.py
Everything it writes (uploads, output, logs) lives under the install folder,
which the installer puts in the user's own profile so it is writable.
"""
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

HOST, PORT = "127.0.0.1", 8000
ROOT = Path(__file__).resolve().parent.parent          # <install>\app
INSTALL = ROOT.parent                                   # <install>


def _port_open() -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((HOST, PORT)) == 0


def _open_when_ready():
    for _ in range(240):                                # up to ~2 minutes
        if _port_open():
            webbrowser.open(f"http://{HOST}:{PORT}/#app")
            return
        time.sleep(0.5)


def main():
    if _port_open():                                    # already running
        webbrowser.open(f"http://{HOST}:{PORT}/#app")
        return

    os.environ["PATH"] = str(INSTALL / "ffmpeg") + os.pathsep + os.environ.get("PATH", "")
    os.environ["OPENSHORTS_DASHBOARD_DIR"] = str(ROOT / "dashboard" / "dist")
    os.environ.setdefault("PYTHONUTF8", "1")
    # Metered connection: audio first, then only the parts of the video that
    # become clips (see smart_download.py). Set OPENSHORTS_SMART_DOWNLOAD=0 in
    # the environment to download whole videos as before.
    os.environ.setdefault("OPENSHORTS_SMART_DOWNLOAD", "1")
    # Campaigns (videos, analytics screenshots, chat) live outside app\ so an
    # update of the program never touches them.
    os.environ.setdefault("OPENSHORTS_DATA_DIR", str(INSTALL / "data"))
    # Jobs are started as [sys.executable, "main.py"]. pythonw.exe has no stdout
    # to pipe back, so jobs must use the console python.exe next to it.
    sys.executable = str(INSTALL / "python" / "python.exe")
    os.chdir(ROOT)                                      # app.py uses relative output/ and uploads/
    sys.path.insert(0, str(ROOT))

    # pythonw has no console: send output to a log file instead of nowhere.
    log = open(INSTALL / "openshorts.log", "a", buffering=1, encoding="utf-8")
    sys.stdout = sys.stderr = log

    threading.Thread(target=_open_when_ready, daemon=True).start()

    import uvicorn
    uvicorn.run("app:app", host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
