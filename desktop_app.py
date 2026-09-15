"""
Desktop App Launcher for Sri Laxmi Gayatri Traders - Invoice ERP
Starts the backend server, verifies health readiness, opens the application
in a dedicated native/desktop window, manages process lifecycles, and cleanly
shuts down all backend processes when the desktop window is closed.
"""
import sys
import os
import time
import socket
import atexit
import json
import urllib.request
import urllib.error
import subprocess
from pathlib import Path

# 1. Resolve project and web directory paths (working directory independent)
ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "web"
LOG_FILE = ROOT_DIR / "desktop_app.log"

def show_message_box(title, message, is_error=False):
    """Display a native Windows dialog box so errors are visible even under pythonw."""
    print(f"[{'ERROR' if is_error else 'INFO'}] {title}: {message}")
    if sys.platform == 'win32':
        try:
            import ctypes
            icon_flag = 0x10 if is_error else 0x40
            ctypes.windll.user32.MessageBoxW(0, str(message), str(title), icon_flag | 0x0)
            return
        except Exception:
            pass
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        if is_error:
            messagebox.showerror(title, message)
        else:
            messagebox.showinfo(title, message)
        root.destroy()
    except Exception:
        pass

def check_dependencies():
    """Verify essential Python dependencies before launching backend."""
    missing = []
    for mod in ['flask', 'flask_cors', 'openpyxl', 'pandas']:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        msg = (
            f"Missing required Python packages: {', '.join(missing)}\n\n"
            f"Please run the following command to install dependencies:\n"
            f"pip install -r \"{ROOT_DIR / 'requirements.txt'}\""
        )
        show_message_box("Invoice ERP - Missing Dependencies", msg, is_error=True)
        sys.exit(1)

def is_port_in_use(port):
    """Check whether a local TCP port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0

def check_existing_erp_instance(port):
    """Check if an existing instance of our ERP is running on the given port."""
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/status", headers={'User-Agent': 'DesktopLauncher'})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('success') and ('Invoice ERP' in data.get('app_name', '') or 'engine' in data):
                    return True
    except Exception:
        pass
    return False

def find_available_port(start_port=5000, max_attempts=20):
    """Find an available port starting from start_port."""
    for p in range(start_port, start_port + max_attempts):
        if not is_port_in_use(p):
            return p
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def get_chromium_browser_path():
    """Search for Edge, Chrome, and Chromium executables on Windows."""
    candidates = []

    # Priority 1: Check Microsoft Edge paths
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")
    ]
    edge_core_base = Path(r"C:\Program Files (x86)\Microsoft\EdgeCore")
    if edge_core_base.exists():
        for sub in edge_core_base.iterdir():
            edge_bin = sub / "msedge.exe"
            if edge_bin.exists():
                edge_paths.append(str(edge_bin))

    # Priority 2: Google Chrome paths
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]

    # Priority 3: Brave
    brave_paths = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe")
    ]

    for p in edge_paths + chrome_paths + brave_paths:
        if p and os.path.exists(p):
            return p

    for name in ['msedge.exe', 'chrome.exe', 'brave.exe']:
        try:
            out = subprocess.check_output(['where.exe', name], stderr=subprocess.DEVNULL, text=True)
            first_line = out.strip().splitlines()[0]
            if os.path.exists(first_line):
                return first_line
        except Exception:
            pass

    return None

def main():
    # Verify core files exist
    if not (WEB_DIR / "app.py").exists() or not (WEB_DIR / "index.html").exists():
        show_message_box(
            "Invoice ERP - File Missing",
            f"Required application files not found in:\n{WEB_DIR}\n\nPlease check repository installation.",
            is_error=True
        )
        sys.exit(1)

    check_dependencies()

    # Configure local SQLite environment
    env = os.environ.copy()
    env['DATABASE_ENGINE'] = 'sqlite'
    env['DESKTOP_MODE'] = '1'
    for k in ['DATABASE_URL', 'POSTGRES_URL', 'POSTGRESQL_URL']:
        env.pop(k, None)

    # Determine port
    default_port = 5000
    backend_proc = None
    managed_by_us = True

    if is_port_in_use(default_port):
        if check_existing_erp_instance(default_port):
            print(f"ℹ️ Existing healthy Invoice ERP backend detected on port {default_port}.")
            port = default_port
            managed_by_us = False
        else:
            print(f"⚠️ Port {default_port} is occupied by another application. Selecting alternate port...")
            port = find_available_port(5001)
    else:
        port = default_port

    env['PORT'] = str(port)
    app_url = f"http://127.0.0.1:{port}"

    def cleanup_backend():
        nonlocal backend_proc
        if backend_proc and backend_proc.poll() is None:
            print("🛑 Shutting down Invoice ERP backend process...")
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{port}/api/desktop/shutdown", method='POST')
                urllib.request.urlopen(req, timeout=1.5)
            except Exception:
                pass
            try:
                backend_proc.terminate()
                backend_proc.wait(timeout=2.0)
            except Exception:
                try:
                    backend_proc.kill()
                except Exception:
                    pass
            backend_proc = None

    atexit.register(cleanup_backend)

    # Start backend subprocess if not already running
    if managed_by_us:
        print(f"🚀 Starting Invoice ERP backend on {app_url}...")
        try:
            log_handle = open(LOG_FILE, "w", encoding="utf-8")
            creationflags = 0x08000000 if sys.platform == 'win32' else 0
            backend_proc = subprocess.Popen(
                [sys.executable, str(WEB_DIR / "app.py")],
                cwd=str(WEB_DIR),
                env=env,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                creationflags=creationflags
            )
        except Exception as e:
            show_message_box("Invoice ERP - Startup Error", f"Failed to start backend process:\n{e}", is_error=True)
            sys.exit(1)

        print("⏳ Waiting for backend health check...")
        ready = False
        start_wait = time.time()
        while time.time() - start_wait < 35:
            if backend_proc.poll() is not None:
                log_snippet = ""
                try:
                    if LOG_FILE.exists():
                        lines = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
                        log_snippet = "\n".join(lines[-15:])
                except Exception:
                    pass
                msg = (
                    f"Backend process terminated unexpectedly (exit code {backend_proc.returncode}).\n\n"
                    f"Details from log:\n{log_snippet or 'No log details available.'}"
                )
                show_message_box("Invoice ERP - Backend Failed", msg, is_error=True)
                sys.exit(1)

            try:
                req = urllib.request.Request(f"{app_url}/api/status", headers={'User-Agent': 'DesktopLauncher'})
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    if resp.status == 200:
                        ready = True
                        break
            except Exception:
                pass
            time.sleep(0.3)

        if not ready:
            cleanup_backend()
            show_message_box(
                "Invoice ERP - Timeout",
                f"Backend server did not respond within 35 seconds at {app_url}.\nPlease check {LOG_FILE.name}.",
                is_error=True
            )
            sys.exit(1)
        print("✅ Backend is ready and healthy!")

    # Priority 1: Native WebView window if pywebview is available
    try:
        import webview
        print("🖥️  Opening native window via pywebview...")
        webview.create_window(
            "Sri Laxmi Gayatri Traders - Invoice ERP",
            app_url,
            width=1280,
            height=850,
            min_size=(900, 600)
        )
        webview.start()
        print("🖥️  Native window closed by user.")
        cleanup_backend()
        return
    except ImportError:
        print("ℹ️ pywebview not installed. Falling back to Chromium app mode...")
    except Exception as e:
        print(f"⚠️ pywebview launch error: {e}. Falling back to Chromium app mode...")

    # Priority 2: Fallback to Chromium app mode (Chrome/Edge/Brave)
    browser_bin = get_chromium_browser_path()
    if browser_bin:
        browser_name = Path(browser_bin).name
        print(f"🌐 Opening dedicated app window via {browser_name} --app mode...")
        profile_dir = Path(os.path.expandvars(r"%LOCALAPPDATA%\SriLaxmiGayatriTraders\ERP_Profile"))
        profile_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            browser_bin,
            f"--app={app_url}",
            f"--user-data-dir={profile_dir}",
            "--window-size=1280,850",
            "--no-first-run",
            "--no-default-browser-check"
        ]
        browser_proc = subprocess.Popen(cmd)

        time.sleep(1)
        while True:
            if browser_proc.poll() is not None:
                print("🌐 Dedicated desktop window closed by user.")
                break
            if managed_by_us and (backend_proc is None or backend_proc.poll() is not None):
                break
            time.sleep(1.0)

        cleanup_backend()
        return

    # Priority 3: Fallback to system default browser
    print("🌐 Opening in default web browser...")
    import webbrowser
    webbrowser.open(app_url)
    try:
        while managed_by_us and backend_proc and backend_proc.poll() is None:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup_backend()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting Desktop App...")
    except Exception as e:
        show_message_box("Invoice ERP - Unexpected Error", str(e), is_error=True)
        sys.exit(1)
