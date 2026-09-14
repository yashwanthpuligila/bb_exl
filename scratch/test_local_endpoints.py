import urllib.request
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def get(path):
    req = urllib.request.Request(f"{BASE_URL}{path}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))

def post(path, data):
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))

def delete(path):
    req = urllib.request.Request(f"{BASE_URL}{path}", method='DELETE')
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))

def run_tests():
    print("==========================================")
    print("Testing Flask Application with SQLite Mode")
    print("==========================================")

    # 1. Test Dashboard Analytics
    print("\n1. Testing /api/dashboard?range=all...")
    dash = get("/api/dashboard?range=all")
    print(f"   ✓ Success! Invoices: {dash['metrics']['totalInvoices']}, Total Sales: ₹{dash['metrics']['totalSales']:,.2f}")
    assert dash['metrics']['totalInvoices'] >= 7


    # 2. Test Customers Overview
    print("\n2. Testing /api/customers...")
    custs = get("/api/customers")
    print(f"   ✓ Success! Total registered customers: {len(custs['customers'])}")
    assert len(custs['customers']) >= 6

    # 3. Test Products Overview
    print("\n3. Testing /api/products...")
    prods = get("/api/products")
    print(f"   ✓ Success! Total registered products: {len(prods['products'])}")
    assert len(prods['products']) >= 34

    # 4. Test Invoices List
    print("\n4. Testing /api/invoices...")
    invs = get("/api/invoices")
    print(f"   ✓ Success! Total invoices listed: {invs['totalCount']}")
    assert invs['totalCount'] >= 7

    # 5. Test Raw Database Browser
    print("\n5. Testing /api/admin/raw-database...")
    raw = get("/api/admin/raw-database?table=invoices")
    print(f"   ✓ Success! Engine: {raw.get('engine')}, Tables: {[t['name'] for t in raw['tables']]}")
    print(f"   ✓ Selected table rows count: {raw['total_rows']}")
    assert raw['success'] is True

    # 6. Test Creating Invoice - 'Current Bill Only'
    print("\n6. Testing Invoice Creation ('current')...")
    test_inv_current = {
        "customer": {
            "shopName": "Migration Test Store",
            "area": "Hyderabad"
        },
        "products": [
            {"name": "Brass Ball Valve 1/2", "quantity": 10, "price": 250.0},
            {"name": "PVC Pipe 1 inch", "quantity": 5, "price": 120.0}
        ],
        "invoice_type": "current",
        "extra_charges_desc": "Delivery",
        "extra_charges_amount": 50.0
    }
    res_curr = post("/api/generate-invoice", test_inv_current)
    assert res_curr.get('success') is True
    inv_num_1 = res_curr['invoice_number']
    expected_total_1 = (10 * 250.0) + (5 * 120.0) + 50.0  # 2500 + 600 + 50 = 3150
    print(f"   ✓ Invoice created: {inv_num_1}")
    print(f"   ✓ Total calculated: ₹{res_curr['history']['grand_total']} (Expected: ₹{expected_total_1})")
    assert abs(res_curr['history']['grand_total'] - expected_total_1) < 0.01

    # 7. Test Creating Second Invoice - 'All Bills (With History)'
    print("\n7. Testing Second Invoice ('all' - With History)...")
    test_inv_all = {
        "customer": {
            "shopName": "Migration Test Store",
            "area": "Hyderabad"
        },
        "products": [
            {"name": "Teflon Tape", "quantity": 20, "price": 15.0}
        ],
        "invoice_type": "all",
        "extra_charges_desc": "",
        "extra_charges_amount": 0.0
    }
    res_all = post("/api/generate-invoice", test_inv_all)
    assert res_all.get('success') is True
    inv_num_2 = res_all['invoice_number']
    today_order = 20 * 15.0  # 300
    expected_grand_total = expected_total_1 + today_order  # 3150 + 300 = 3450
    prev_orders = res_all['history'].get('previous_orders', [])
    print(f"   ✓ Invoice created: {inv_num_2}")
    print(f"   ✓ Previous orders loaded from DB: {len(prev_orders)}")
    print(f"   ✓ Grand total with history: ₹{res_all['history']['grand_total']} (Expected: ₹{expected_grand_total})")
    assert len(prev_orders) >= 1
    assert abs(res_all['history']['grand_total'] - expected_grand_total) < 0.01

    # 8. Test Download Endpoint (including on-demand regeneration)
    print("\n8. Testing /api/download/<filename>...")
    req = urllib.request.Request(f"{BASE_URL}/api/download/{res_curr['filename']}")
    with urllib.request.urlopen(req) as resp:
        content = resp.read()
        print(f"   ✓ Successfully downloaded invoice Excel ({len(content)} bytes)")
        assert len(content) > 1000

    # 9. Test Deleting Test Invoices
    print("\n9. Testing Invoice Deletion...")
    del_res_1 = delete(f"/api/invoices/{inv_num_1}")
    del_res_2 = delete(f"/api/invoices/{inv_num_2}")
    print(f"   ✓ Deleted {inv_num_1}: {del_res_1.get('success')}")
    print(f"   ✓ Deleted {inv_num_2}: {del_res_2.get('success')}")

    # Remove temporary customer from catalog
    post("/api/customers/Migration%20Test%20Store/all-data", {"confirmation": "Migration Test Store"})

    # 10. Final Verification of Counts
    print("\n10. Final Verification...")
    final_dash = get("/api/dashboard?range=all")
    print(f"   ✓ Total Invoices restored to: {final_dash['metrics']['totalInvoices']}")
    print(f"   ✓ Total Sales: ₹{final_dash['metrics']['totalSales']:,.2f}")


    print("\n==========================================")
    print("🎉 ALL LOCAL ENDPOINT TESTS PASSED 100%!")
    print("==========================================")

if __name__ == '__main__':
    run_tests()
