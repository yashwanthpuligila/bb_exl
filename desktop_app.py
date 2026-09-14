"""
Desktop App Launcher for Invoice Generator ERP
Launches the Flask backend and opens the interface in a dedicated native app window.
"""
import sys
import time
import threading
import urllib.request
import subprocess
import os
from pathlib import Path

# Add web directory to path
ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "web"
sys.path.insert(0, str(WEB_DIR))

def is_server_running(url="http://127.0.0.1:5000/"):
    try:
        with urllib.request.urlopen(url, timeout=1) as resp:
            return resp.status == 200
    except Exception:
        return False

def start_flask():
    os.chdir(str(WEB_DIR))
    from app import app
    # Run without debug reloader in desktop mode
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

def main():
    # If server is not already running, start it in a background thread
    if not is_server_running():
        server_thread = threading.Thread(target=start_flask, daemon=True)
        server_thread.start()
        for _ in range(25):
            if is_server_running():
                break
            time.sleep(0.2)

    app_url = "http://127.0.0.1:5000"

    # Option 1: Native WebView window if pywebview is available
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
        return
    except ImportError:
        pass

    # Option 2: Fallback to Edge or Chrome native app mode (window without address bar)
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]

    browser_bin = None
    for p in edge_paths + chrome_paths:
        if os.path.exists(p):
            browser_bin = p
            break

    if browser_bin:
        print(f"🌐 Opening app window using {os.path.basename(browser_bin)} --app mode...")
        subprocess.run([browser_bin, f"--app={app_url}", "--window-size=1280,850"])
    else:
        import webbrowser
        webbrowser.open(app_url)

if __name__ == "__main__":
    main()
