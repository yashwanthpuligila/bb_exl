import sys
import os
import time
import subprocess
import urllib.request
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT_DIR / "web"
sys.path.insert(0, str(ROOT_DIR / "scratch"))

def main():
    print("==================================================")
    print("STARTING FULL END-TO-END VERIFICATION SUITE")
    print("==================================================")

    env = os.environ.copy()
    env['DATABASE_ENGINE'] = 'sqlite'
    env['DESKTOP_MODE'] = '1'
    env['PORT'] = '5000'
    for k in ['DATABASE_URL', 'POSTGRES_URL', 'POSTGRESQL_URL']:
        env.pop(k, None)

    print("\n1. Spawning Flask Backend in Desktop Mode...")
    proc = subprocess.Popen(
        [sys.executable, str(WEB_DIR / "app.py")],
        cwd=str(WEB_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    app_url = "http://127.0.0.1:5000"
    ready = False
    print("2. Polling Backend Health Check...")
    for _ in range(40):
        if proc.poll() is not None:
            _, err = proc.communicate()
            print("ERROR: Backend crashed immediately:", err.decode('utf-8', errors='ignore'))
            sys.exit(1)
        try:
            with urllib.request.urlopen(f"{app_url}/api/status", timeout=1) as resp:
                if resp.status == 200:
                    status_data = json.loads(resp.read().decode('utf-8'))
                    print("   ✓ Health check succeeded:", status_data)
                    assert status_data['success'] is True
                    assert status_data['engine'] == 'SQLite'
                    assert status_data['desktop_mode'] is True
                    ready = True
                    break
        except Exception:
            pass
        time.sleep(0.3)

    assert ready, "Backend failed to become ready within timeout"

    print("\n3. Testing Desktop Heartbeat Endpoint...")
    req = urllib.request.Request(f"{app_url}/api/desktop/heartbeat?session=test_verify_session", method='POST')
    with urllib.request.urlopen(req, timeout=2) as resp:
        hb_data = json.loads(resp.read().decode('utf-8'))
        print("   ✓ Heartbeat response:", hb_data)
        assert hb_data['status'] == 'ok'

    try:
        print("\n4. Running Existing Local Endpoints Verification Suite...")
        import test_local_endpoints
        test_local_endpoints.run_tests()
        print("   ✓ All existing database and invoice features verified!")

        print("\n5. Testing Graceful Desktop Shutdown Endpoint...")
        req = urllib.request.Request(f"{app_url}/api/desktop/shutdown?session=test_verify_session", method='POST')
        with urllib.request.urlopen(req, timeout=2) as resp:
            sd_data = json.loads(resp.read().decode('utf-8'))
            print("   ✓ Shutdown response:", sd_data)

        print("6. Waiting for backend clean process exit...")
        try:
            proc.wait(timeout=6)
            print(f"   ✓ Backend process terminated cleanly with returncode: {proc.returncode}")
        except subprocess.TimeoutExpired:
            proc.kill()
            raise AssertionError("Backend process did not terminate within shutdown window")

        print("\n7. Verifying Port 5000 is released...")
        time.sleep(1)
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            in_use = s.connect_ex(('127.0.0.1', 5000)) == 0
            assert not in_use, "Port 5000 must be released after shutdown"
            print("   ✓ Port 5000 is completely released!")

        print("\n==================================================")
        print("🎉 ALL TESTS PASSED! FULL END-TO-END VERIFICATION SUCCESSFUL")
        print("==================================================")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except Exception:
                proc.kill()

if __name__ == '__main__':
    main()
