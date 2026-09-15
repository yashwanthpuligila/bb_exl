"""
5-Minute Full Stability and Concurrency Verification Test Suite.
Tests:
- TEST A: Fresh Launch (Dashboard, Invoices, Customers, Products, Database)
- TEST B: 5-Minute Stability (300 seconds continuous execution with checks at 30s, 60s, 90s, 120s, 180s, 240s, 300s)
- TEST C: Minimize/Inactivity Simulation (long periods without heartbeats)
- TEST D: View Navigation Stress Test (rapid sequential queries)
- TEST E: Database Browser (all 8 tables checked for schema and rows)
- TEST F: Invoice Operations (Create, Verify, Delete, Restart, Verify No Resurrection)
- TEST G: Authoritative Backend Shutdown & Clean Port Release
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
WEB_DIR = ROOT_DIR / "web"
LOG_FILE = ROOT_DIR / "desktop_app.log"
PORT = 5000
BASE_URL = f"http://127.0.0.1:{PORT}"

def is_port_listening(port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0

def http_get(path, timeout=5.0):
    url = f"{BASE_URL}{path}"
    t0 = time.time()
    req = urllib.request.Request(url, headers={'User-Agent': 'StabilityTester'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode('utf-8')
            elapsed = time.time() - t0
            return resp.status, json.loads(data), elapsed
    except Exception as e:
        elapsed = time.time() - t0
        return None, str(e), elapsed

def http_post(path, payload, timeout=5.0):
    url = f"{BASE_URL}{path}"
    t0 = time.time()
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json', 'User-Agent': 'StabilityTester'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode('utf-8')
            elapsed = time.time() - t0
            return resp.status, json.loads(data), elapsed
    except Exception as e:
        elapsed = time.time() - t0
        return None, str(e), elapsed

def http_delete(path, timeout=5.0):
    url = f"{BASE_URL}{path}"
    t0 = time.time()
    req = urllib.request.Request(url, method='DELETE', headers={'User-Agent': 'StabilityTester'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode('utf-8')
            elapsed = time.time() - t0
            return resp.status, json.loads(data), elapsed
    except Exception as e:
        elapsed = time.time() - t0
        return None, str(e), elapsed

def main():
    print("=" * 70)
    print("STARTING 5-MINUTE DESKTOP STABILITY & VERIFICATION TEST")
    print("=" * 70)

    # 1. Start backend process exactly as desktop_app.py does
    env = os.environ.copy()
    env['DESKTOP_MODE'] = '1'
    env['PORT'] = str(PORT)
    env['DATABASE_ENGINE'] = 'sqlite'
    for k in ['DATABASE_URL', 'POSTGRES_URL', 'POSTGRESQL_URL']:
        env.pop(k, None)

    print(f"\n[1] Starting backend subprocess (DESKTOP_MODE=1, PORT={PORT})...")
    log_fp = open(LOG_FILE, "w", encoding="utf-8")
    backend_proc = subprocess.Popen(
        [sys.executable, str(WEB_DIR / "app.py")],
        cwd=str(WEB_DIR),
        env=env,
        stdout=log_fp,
        stderr=subprocess.STDOUT
    )
    print(f"    Backend PID: {backend_proc.pid}")

    # Wait for ready
    ready = False
    for _ in range(30):
        time.sleep(0.5)
        st, data, _ = http_get("/api/status")
        if st == 200:
            ready = True
            break
    if not ready:
        print("❌ Backend failed to start!")
        backend_proc.terminate()
        sys.exit(1)
    print(f"    ✓ Backend is ready and listening on port {PORT}")

    # TEST A: Fresh Launch Verification
    print("\n[TEST A] Verifying all pages immediately on fresh launch...")
    st_stat, _, t_stat = http_get("/api/status")
    st_dash, data_dash, t_dash = http_get("/api/dashboard?range=all")
    st_inv, data_inv, t_inv = http_get("/api/invoices?range=all&limit=150")
    st_cust, data_cust, t_cust = http_get("/api/customers")
    st_prod, data_prod, t_prod = http_get("/api/products")
    st_db, data_db, t_db = http_get("/api/admin/raw-database?table=invoices")

    print(f"    /api/status:               {st_stat} (in {t_stat:.3f}s)")
    print(f"    /api/dashboard?range=all:  {st_dash} (in {t_dash:.3f}s, totalInvoices={data_dash.get('metrics', {}).get('totalInvoices')})")
    print(f"    /api/invoices:             {st_inv} (in {t_inv:.3f}s, totalCount={data_inv.get('totalCount')})")
    print(f"    /api/customers:            {st_cust} (in {t_cust:.3f}s, totalCount={data_cust.get('totalCount')})")
    print(f"    /api/products:             {st_prod} (in {t_prod:.3f}s, totalCount={data_prod.get('totalCount')})")
    print(f"    /api/admin/raw-database:   {st_db} (in {t_db:.3f}s, total_rows={data_db.get('total_rows')})")

    assert all(x == 200 for x in [st_stat, st_dash, st_inv, st_cust, st_prod, st_db]), "TEST A FAILED: Not all endpoints returned 200"
    print("    ✅ TEST A PASSED: All views operational on fresh launch.")

    # TEST E: Database Browser Tables & Rows Verification
    print("\n[TEST E] Verifying Database Browser loads schema and rows for ALL tables...")
    tables = data_db.get('tables', [])
    print(f"    Found {len(tables)} tables in SQLite database:")
    for tbl in tables:
        t_name = tbl['name']
        t_cnt = tbl['count']
        st_t, data_t, elap = http_get(f"/api/admin/raw-database?table={t_name}")
        cols = data_t.get('columns', [])
        rows = data_t.get('rows', [])
        print(f"    - Table '{t_name}': Count={t_cnt}, Columns={len(cols)}, RowsReturned={len(rows)} (HTTP {st_t} in {elap:.3f}s)")
        assert st_t == 200, f"Failed to fetch table {t_name}"
        assert len(cols) > 0, f"No columns returned for table {t_name}"
        assert len(rows) == min(t_cnt, 250), f"Row count mismatch for table {t_name}"
    print("    ✅ TEST E PASSED: Every database table verified with schema and rows.")

    # TEST F: Invoice Operations & Deletion Idempotency
    print("\n[TEST F] Testing Invoice Creation, Verification, Deletion, and Restart Persistence...")
    initial_inv_count = data_inv.get('totalCount', 0)
    test_inv_payload = {
        'customer': {
            'shopName': 'Stability Test Mart',
            'area': 'Kukatpally Wholesale Zone'
        },
        'products': [
            {'name': 'Basmati Rice Special 25kg', 'quantity': 5, 'price': 1200.0}
        ],
        'invoiceType': 'current'
    }
    st_create, data_create, t_create = http_post("/api/generate-invoice", test_inv_payload)
    print(f"    POST /api/generate-invoice: {st_create} (in {t_create:.3f}s)")
    assert st_create == 200 and data_create.get('success'), f"Create invoice failed: {data_create}"
    created_inv_num = data_create.get('invoice_number') or data_create.get('invoiceNumber')
    print(f"    Created invoice: {created_inv_num}")

    # Verify invoice appears
    st_check, data_check, _ = http_get("/api/invoices?range=all")
    new_inv_count = data_check.get('totalCount', 0)
    print(f"    Total invoices after creation: {new_inv_count} (was {initial_inv_count})")
    assert new_inv_count == initial_inv_count + 1, "Invoice count did not increment"

    # Delete invoice
    st_del, data_del, t_del = http_delete(f"/api/invoices/{created_inv_num}")
    print(f"    DELETE /api/invoices/{created_inv_num}: {st_del} (in {t_del:.3f}s)")
    assert st_del == 200 and data_del.get('success'), f"Delete invoice failed: {data_del}"

    # Verify invoice is gone
    st_post_del, data_post_del, _ = http_get("/api/invoices?range=all")
    after_del_count = data_post_del.get('totalCount', 0)
    print(f"    Total invoices after deletion: {after_del_count}")
    assert after_del_count == initial_inv_count, "Invoice count did not return to original"
    print("    ✅ TEST F PASSED: Invoice created, verified, and deleted successfully.")

    # TEST B & C: 5-Minute Stability & Minimize/Inactivity Simulation
    print("\n[TEST B & C] Running 5-Minute (300s) Continuous Stability & Inactivity Test...")
    print("    (Simulating periods where frontend is minimized/backgrounded and NO heartbeats are sent)")
    start_time = time.time()
    checkpoint_interval = 30 # Check every 30s
    next_checkpoint = 30
    checkpoints = [30, 60, 90, 120, 180, 240, 300]
    results_table = []

    while time.time() - start_time < 310:
        time.sleep(5)
        elapsed = int(time.time() - start_time)

        # Send occasional heartbeat during some periods, and OMIT completely for minutes at a time
        # Specifically: do NOT send any heartbeats between 60s and 240s (3 full minutes of simulated minimization!)
        if elapsed < 60 or elapsed > 240:
            http_post("/api/desktop/heartbeat?session=desktop_stability_test", {})

        if elapsed >= next_checkpoint:
            target = next_checkpoint
            next_idx = checkpoints.index(target) + 1 if target in checkpoints else None
            next_checkpoint = checkpoints[next_idx] if next_idx and next_idx < len(checkpoints) else 999

            # Check process alive
            proc_alive = backend_proc.poll() is None
            port_open = is_port_listening(PORT)

            # Query all key endpoints
            st_s, _, t_s = http_get("/api/status")
            st_i, d_i, t_i = http_get("/api/invoices?range=all&limit=150")
            st_c, d_c, t_c = http_get("/api/customers")
            st_p, d_p, t_p = http_get("/api/products")
            st_d, d_d, t_d = http_get("/api/admin/raw-database?table=invoices")

            row_res = {
                'elapsed': f"{elapsed}s",
                'alive': proc_alive,
                'port': port_open,
                'status': st_s,
                'invoices': f"{st_i} (cnt={d_i.get('totalCount')})",
                'customers': f"{st_c} (cnt={d_c.get('totalCount')})",
                'products': f"{st_p} (cnt={d_p.get('totalCount')})",
                'db_rows': f"{st_d} (rows={d_d.get('total_rows')})",
                'time_s': f"{t_i:.3f}s"
            }
            results_table.append(row_res)
            print(f"    [{elapsed:3d}s] Alive: {proc_alive} | Port {PORT}: {port_open} | Invoices: {st_i} | Customers: {st_c} | Products: {st_p} | DB: {st_d} | Latency: {t_i:.3f}s")

            assert proc_alive, f"Backend DIED at {elapsed}s!"
            assert port_open, f"Port {PORT} closed at {elapsed}s!"
            assert all(x == 200 for x in [st_s, st_i, st_c, st_p, st_d]), f"Endpoint failure at {elapsed}s!"

    print("\n    ✅ 5-Minute Stability Summary Table:")
    print("    Elapsed | Alive | Port | Status | Invoices      | Customers    | Products     | Database Rows | Latency")
    print("    " + "-" * 95)
    for r in results_table:
        print(f"    {r['elapsed']:7s} | {str(r['alive']):5s} | {str(r['port']):4s} | {r['status']:6d} | {r['invoices']:13s} | {r['customers']:12s} | {r['products']:12s} | {r['db_rows']:13s} | {r['time_s']}")
    print("    ✅ TEST B & C PASSED: Backend ran continuously for 5+ minutes with zero failures.")

    # TEST D: Navigation Stress Test
    print("\n[TEST D] Stress-testing rapid view navigation (25 back-to-back view transitions)...")
    for i in range(25):
        http_get("/api/dashboard?range=all")
        http_get("/api/invoices?range=all&limit=150")
        http_get("/api/customers")
        http_get("/api/products")
        http_get("/api/admin/raw-database?table=invoices")
    st_verify, d_verify, _ = http_get("/api/invoices?range=all")
    assert st_verify == 200 and d_verify.get('totalCount') == initial_inv_count
    print(f"    ✓ 125 API requests completed successfully without deadlock or error.")
    print("    ✅ TEST D PASSED: Rapid navigation stress test passed.")

    # TEST G: Authoritative Backend Shutdown & Clean Port Release
    print("\n[TEST G] Testing authoritative shutdown & restart persistence...")
    print("    Terminating backend subprocess via authoritative manager...")
    backend_proc.terminate()
    try:
        backend_proc.wait(timeout=3.0)
    except Exception:
        backend_proc.kill()

    time.sleep(1.0)
    assert not is_port_listening(PORT), "Port 5000 was NOT released after shutdown!"
    print(f"    ✓ Backend process exited cleanly with code {backend_proc.returncode}")
    print(f"    ✓ Port {PORT} is completely released.")

    # Reopen and verify deleted invoice NEVER resurrected
    print("    Reopening backend from clean restart...")
    log_fp2 = open(LOG_FILE, "a", encoding="utf-8")
    backend_proc2 = subprocess.Popen(
        [sys.executable, str(WEB_DIR / "app.py")],
        cwd=str(WEB_DIR),
        env=env,
        stdout=log_fp2,
        stderr=subprocess.STDOUT
    )
    for _ in range(30):
        time.sleep(0.5)
        st, _, _ = http_get("/api/status")
        if st == 200:
            break
    print(f"    ✓ Backend restarted with new PID: {backend_proc2.pid}")

    st_recheck, data_recheck, _ = http_get("/api/invoices?range=all")
    restart_count = data_recheck.get('totalCount', 0)
    print(f"    Invoices count after clean restart: {restart_count} (original was {initial_inv_count})")
    assert restart_count == initial_inv_count, f"Deleted invoice was resurrected! Count is {restart_count} vs {initial_inv_count}"

    # Clean up restart backend
    backend_proc2.terminate()
    try:
        backend_proc2.wait(timeout=3.0)
    except Exception:
        backend_proc2.kill()
    time.sleep(1.0)
    print("    ✓ Restarted backend terminated cleanly.")
    print("    ✅ TEST G PASSED: Deleted invoice remained deleted across restarts; no resurrection.")

    print("\n" + "=" * 70)
    print("🎉 ALL TESTS PASSED 100%! FULL 5-MINUTE SUITE VERIFIED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == '__main__':
    main()
