"""Vexxo Clip desktop launcher (Windows, no Docker).

Starts the local backend, then shows the app in its own window (not a browser
tab): a native WebView2 window through pywebview, or, if that is not available,
an Edge/Chrome "app mode" window without tabs or address bar. As a last resort
it opens the default browser. Closing the window stops the backend.

Run by the Start-menu shortcut as:  python\\pythonw.exe desktop\\launcher.py
Everything it writes (uploads, output, logs, window data) lives under the install
folder, which the installer puts in the user's profile so it is writable.
"""
import ctypes
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

HOST, PORT = "127.0.0.1", 8000
TITLE = "Vexxo Clip"
URL = f"http://{HOST}:{PORT}/#app"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                                      # <install>\app
INSTALL = ROOT.parent                                   # <install>
SPLASH = HERE / "splash.html"
ICON = HERE / "vexxo.ico"
WINDOW_SIZE = (1360, 860)
MIN_SIZE = (1000, 640)


def _port_open() -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((HOST, PORT)) == 0


def _prepare_env():
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
    exe = INSTALL / "python" / "python.exe"
    if exe.exists():
        sys.executable = str(exe)
    os.chdir(ROOT)                                      # app.py uses relative output/ and uploads/
    sys.path.insert(0, str(ROOT))
    # pythonw has no console: send output to a log file instead of nowhere.
    log = open(INSTALL / "vexxo.log", "a", buffering=1, encoding="utf-8")
    sys.stdout = sys.stderr = log


def _start_server():
    """Run uvicorn in a background thread; returns (server, thread)."""
    import uvicorn
    server = uvicorn.Server(uvicorn.Config("app:app", host=HOST, port=PORT, log_level="info"))
    thread = threading.Thread(target=server.run, name="backend", daemon=True)
    thread.start()
    return server, thread


def _set_window_icon():
    """Give the native window (and its taskbar button) the Vexxo icon."""
    if os.name != "nt" or not ICON.exists():
        return
    user32 = ctypes.windll.user32
    for _ in range(50):                                 # the window appears a moment after start
        hwnd = user32.FindWindowW(None, TITLE)
        if hwnd:
            for kind, px in ((1, 48), (0, 16)):         # ICON_BIG, ICON_SMALL
                handle = user32.LoadImageW(None, str(ICON), 1, px, px, 0x10)   # IMAGE_ICON, LR_LOADFROMFILE
                if handle:
                    user32.SendMessageW(hwnd, 0x80, kind, handle)               # WM_SETICON
            return
        time.sleep(0.2)


def _run_native_window(confirm_close: bool) -> bool:
    """Show the app in a WebView2 window. True if a window ran and was closed."""
    try:
        import webview
        webview.settings["ALLOW_DOWNLOADS"] = True      # "download clips" buttons
        webview.create_window(
            TITLE, html=SPLASH.read_text(encoding="utf-8"),
            width=WINDOW_SIZE[0], height=WINDOW_SIZE[1], min_size=MIN_SIZE,
            background_color="#0B0D14", text_select=True, confirm_close=confirm_close)
        started = time.time()
        webview.start(
            func=_set_window_icon, gui="edgechromium",
            private_mode=False,                         # keep localStorage (API key, active campaign)
            storage_path=str(INSTALL / "webview-data"))
        return time.time() - started > 3                # returning at once means it never opened
    except BaseException as e:                          # incl. SystemExit from a missing runtime
        print(f"native window unavailable ({type(e).__name__}: {e})")
        return False


def _find_chromium():
    names = [("Microsoft", "Edge", "Application", "msedge.exe"),
             ("Google", "Chrome", "Application", "chrome.exe")]
    for var in ("ProgramFiles(x86)", "ProgramFiles", "LocalAppData"):
        base = os.environ.get(var)
        for parts in names:
            if base and (Path(base).joinpath(*parts)).exists():
                return str(Path(base).joinpath(*parts))
    return None


def _run_chromium_app_window() -> bool:
    """Edge/Chrome in app mode: a plain window, no tabs, no address bar."""
    exe = _find_chromium()
    if not exe:
        return False
    started = time.time()
    try:
        proc = subprocess.Popen([
            exe, f"--app={SPLASH.as_uri()}", f"--user-data-dir={INSTALL / 'app-profile'}",
            f"--window-size={WINDOW_SIZE[0]},{WINDOW_SIZE[1]}",
            "--no-first-run", "--no-default-browser-check"])
        proc.wait()
    except OSError as e:
        print(f"app window unavailable ({e})")
        return False
    return time.time() - started > 3


def _quit_everything():
    """Stop the backend and any job it started."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(os.getpid())],
                       creationflags=0x08000000, check=False)   # CREATE_NO_WINDOW
    os._exit(0)


def main():
    if os.name == "nt":
        try:                                            # own taskbar identity, not "Python"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Vexxo.Clip")
        except Exception:
            pass

    own_server = not _port_open()
    server = thread = None
    if own_server:
        _prepare_env()
        server, thread = _start_server()

    shown = _run_native_window(confirm_close=own_server) or _run_chromium_app_window()
    if not shown:
        # Last resort: the default browser. Keep serving until the process is stopped.
        while own_server and not _port_open():
            time.sleep(0.5)
        webbrowser.open(URL)
        if thread:
            thread.join()
        return
    if own_server:
        server.should_exit = True
        _quit_everything()


if __name__ == "__main__":
    main()
