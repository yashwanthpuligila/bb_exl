"""
Reproduction script:
Demonstrates the exact failure mechanism:
1. Start web/app.py in DESKTOP_MODE=1
2. Connect and send heartbeats for 10 seconds (frontend connected)
3. Pause heartbeats for > 8 seconds (simulating browser background timer throttling / window minimize / busy event loop)
4. Record exact failure time, process alive status, exit code, port listening status, and endpoint failure responses.
"""
import sys
import os
import time
import socket
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

ROOT_DIR = Path("d:/BB_EXL").resolve()
WEB_DIR = ROOT_DIR / "web"

def is_port_listening(port=5000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0

def check_endpoint(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'TestRunner'})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status, resp.read().decode('utf-8')[:100]
    except urllib.error.HTTPError as e:
        return e.code, f"HTTPError: {e.reason}"
    except urllib.error.URLError as e:
        return None, f"URLError: {e.reason}"
    except Exception as e:
        return None, f"Exception: {str(e)}"

def main():
    print("==================================================")
    print("REPRODUCING EXACT BACKEND SHUTDOWN ROOT CAUSE")
    print("==================================================")
    
    env = os.environ.copy()
    env['DESKTOP_MODE'] = '1'
    env['PORT'] = '5000'
    env['DATABASE_ENGINE'] = 'sqlite'
    
    # Start backend
    proc = subprocess.Popen(
        [sys.executable, str(WEB_DIR / "app.py")],
        cwd=str(WEB_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    print(f"1. Flask backend started with PID: {proc.pid}")
    
    # Wait for readiness
    ready = False
    for _ in range(30):
        time.sleep(0.5)
        st, _ = check_endpoint("http://127.0.0.1:5000/api/status")
        if st == 200:
            ready = True
            break
            
    print(f"2. Backend ready: {ready}, Port 5000 listening: {is_port_listening(5000)}")
    
    # Send heartbeats for 10 seconds (simulating active frontend)
    print("3. Sending heartbeats every 2.5s for 10s (simulating active window)...")
    for i in range(4):
        time.sleep(2.5)
        st, body = check_endpoint("http://127.0.0.1:5000/api/desktop/heartbeat")
        print(f"   Heartbeat {i+1} response: {st}")
        
    print(f"   State after 10s: Backend PID {proc.pid} poll={proc.poll()}, Port 5000={is_port_listening(5000)}")
    
    # Now simulate window being minimized, inactive, or timer throttled by Chromium (NO heartbeats for 10s)
    print("\n4. SIMULATING WINDOW MINIMIZED / INACTIVE (pausing heartbeats for 10 seconds)...")
    start_pause = time.time()
    while time.time() - start_pause < 12:
        time.sleep(1)
        elapsed_pause = int(time.time() - start_pause)
        ret = proc.poll()
        listening = is_port_listening(5000)
        print(f"   [{elapsed_pause:2d}s without heartbeat] Process alive: {ret is None} (retcode={ret}), Port 5000: {listening}")
        if ret is not None:
            print(f"\n🚨 EXACT MOMENT OF FAILURE: Backend PID {proc.pid} EXITED with code {ret} at {elapsed_pause}s without heartbeat!")
            break
            
    print("\n5. Testing endpoints immediately after failure:")
    for ep in ["/api/status", "/api/invoices", "/api/customers", "/api/products", "/api/admin/raw-database?table=invoices"]:
        st, msg = check_endpoint(f"http://127.0.0.1:5000{ep}")
        print(f"   Endpoint {ep}: Status={st}, Error={msg}")
        
    # Read backend output
    try:
        out, _ = proc.communicate(timeout=2)
        print("\n6. Backend stdout/stderr captured at exit:")
        for line in out.splitlines()[-15:]:
            print("   [BACKEND LOG]", line)
    except Exception as e:
        print("   Could not read stdout:", e)

if __name__ == '__main__':
    main()
