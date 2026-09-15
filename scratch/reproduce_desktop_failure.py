"""
Reproduction script for BB_EXL desktop app 1-2 minute failure.
Monitors:
- desktop_app.py process
- Flask backend process (web/app.py)
- Port 5000 listening status
- HTTP status of /api/status, /api/invoices, /api/customers, /api/products, /api/admin/raw-database
- Captures stdout/stderr/log output and timestamps
"""
import sys
import os
import time
import json
import socket
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

ROOT_DIR = Path("d:/BB_EXL").resolve()
LOG_FILE = ROOT_DIR / "desktop_app.log"

def is_port_listening(port=5000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0

def check_endpoint(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ReproMonitor'})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status, resp.read().decode('utf-8')[:120]
    except urllib.error.HTTPError as e:
        return e.code, f"HTTPError: {e.reason}"
    except urllib.error.URLError as e:
        return None, f"URLError: {e.reason}"
    except Exception as e:
        return None, f"Exception: {str(e)}"

def get_python_processes():
    # Return dict of {pid: cmdline}
    procs = {}
    try:
        out = subprocess.check_output(
            ['powershell', '-Command', 'Get-CimInstance Win32_Process -Filter "Name LIKE \'python%\'" | Select-Object ProcessId, CommandLine | ConvertTo-Json'],
            text=True, errors='ignore'
        )
        data = json.loads(out)
        if isinstance(data, dict):
            data = [data]
        for item in data:
            pid = item.get('ProcessId')
            cmd = item.get('CommandLine') or ''
            procs[pid] = cmd
    except Exception as e:
        pass
    return procs

def main():
    print("==================================================")
    print("STEP 1: Starting desktop_app.py to reproduce issue")
    print("==================================================")
    
    # Ensure port 5000 is clean before start
    if is_port_listening(5000):
        print("Port 5000 is already in use! Checking who owns it...")
        # attempt to query status
        st, body = check_endpoint("http://127.0.0.1:5000/api/status")
        print(f"Status: {st}, Body: {body}")
        
    start_time = time.time()
    desktop_proc = subprocess.Popen(
        [sys.executable, str(ROOT_DIR / "desktop_app.py")],
        cwd=str(ROOT_DIR)
    )
    print(f"Launched desktop_app.py with PID: {desktop_proc.pid}")
    
    # Wait for backend to spin up
    backend_pid = None
    print("Waiting for backend process to be detected...")
    for _ in range(20):
        time.sleep(1)
        procs = get_python_processes()
        for pid, cmd in procs.items():
            if "web" in cmd and "app.py" in cmd:
                backend_pid = pid
                break
        if backend_pid and is_port_listening(5000):
            break
            
    print(f"Backend detected! Backend PID: {backend_pid}, Port 5000 listening: {is_port_listening(5000)}")
    
    # Monitor for up to 150 seconds (2.5 minutes)
    failure_observed = False
    print("\n--- Beginning continuous monitoring for 150 seconds ---")
    for sec in range(0, 155, 5):
        time.sleep(5)
        elapsed = int(time.time() - start_time)
        port_open = is_port_listening(5000)
        
        # Check backend process alive
        backend_alive = False
        if backend_pid:
            try:
                # On Windows check if process still exists
                res = subprocess.run(['powershell', '-Command', f'Get-Process -Id {backend_pid} -ErrorAction SilentlyContinue'], capture_output=True, text=True)
                backend_alive = bool(res.stdout.strip())
            except Exception:
                pass
                
        # Test endpoints
        status_code, status_body = check_endpoint("http://127.0.0.1:5000/api/status")
        inv_code, inv_body = check_endpoint("http://127.0.0.1:5000/api/invoices")
        cust_code, cust_body = check_endpoint("http://127.0.0.1:5000/api/customers")
        prod_code, prod_body = check_endpoint("http://127.0.0.1:5000/api/products")
        db_code, db_body = check_endpoint("http://127.0.0.1:5000/api/admin/raw-database?table=invoices")
        
        print(f"[{elapsed:3d}s] Backend Alive: {backend_alive} (PID: {backend_pid}) | Port 5000: {port_open} | /api/status: {status_code} | /api/invoices: {inv_code} | /api/customers: {cust_code} | /api/db: {db_code}")
        
        if not backend_alive or not port_open or status_code is None or inv_code is None:
            print("\n🚨 FAILURE DETECTED AT ELAPSED TIME:", elapsed, "seconds!")
            print(f"Backend Alive: {backend_alive}")
            print(f"Port 5000 Listening: {port_open}")
            print(f"/api/status: {status_code} -> {status_body}")
            print(f"/api/invoices: {inv_code} -> {inv_body}")
            print(f"/api/customers: {cust_code} -> {cust_body}")
            print(f"/api/products: {prod_code} -> {prod_body}")
            print(f"/api/admin/raw-database: {db_code} -> {db_body}")
            
            # Read desktop_app.log
            if LOG_FILE.exists():
                print("\n--- BACKEND LOG (desktop_app.log) LAST 30 LINES ---")
                lines = LOG_FILE.read_text(encoding='utf-8', errors='ignore').splitlines()
                for line in lines[-30:]:
                    print("LOG:", line)
            
            failure_observed = True
            break
            
    if not failure_observed:
        print("\nNo failure observed within 150 seconds. Will inspect further.")
        
    # Terminate desktop_proc if still running
    if desktop_proc.poll() is None:
        desktop_proc.terminate()
        try:
            desktop_proc.wait(timeout=3)
        except Exception:
            desktop_proc.kill()

if __name__ == '__main__':
    main()
