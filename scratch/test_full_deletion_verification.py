import sys
import os
import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def test_delete_features():
    print("==================================================")
    print("Testing Invoice Generator Delete Features")
    print("==================================================")

    # 1. Create Invoice 1
    inv1_payload = {
        "customer": {
            "shopName": "Test Customer Alpha",
            "area": "Kukatpally Wholesale"
        },
        "products": [
            {"productName": "Alpha Pipe 1-inch", "quantity": 10, "price": 120.0},
            {"productName": "Alpha Fitting 90-deg", "quantity": 5, "price": 40.0}
        ]
    }
    r1 = requests.post(f"{BASE_URL}/api/generate-invoice", json=inv1_payload)
    assert r1.status_code == 200, f"Failed to create invoice 1: {r1.text}"
    inv1_data = r1.json()
    assert inv1_data.get('success'), f"Invoice 1 creation unsuccessful: {inv1_data}"
    inv1_num = inv1_data['invoice_number']
    r_inv1_get = requests.get(f"{BASE_URL}/api/invoices/{inv1_num}").json()
    inv1_total = r_inv1_get['invoice']['totalAmount']
    print(f"Created Invoice 1: {inv1_num} (Total: ₹{inv1_total})")

    # 2. Create Invoice 2
    inv2_payload = {
        "customer": {
            "shopName": "Test Customer Beta",
            "area": "Secunderabad Station"
        },
        "products": [
            {"productName": "Beta Paint Primer", "quantity": 4, "price": 250.0}
        ]
    }
    r2 = requests.post(f"{BASE_URL}/api/generate-invoice", json=inv2_payload)
    assert r2.status_code == 200, f"Failed to create invoice 2: {r2.text}"
    inv2_data = r2.json()
    assert inv2_data.get('success'), f"Invoice 2 creation unsuccessful: {inv2_data}"
    inv2_num = inv2_data['invoice_number']
    r_inv2_get = requests.get(f"{BASE_URL}/api/invoices/{inv2_num}").json()
    inv2_total = r_inv2_get['invoice']['totalAmount']
    print(f"Created Invoice 2: {inv2_num} (Total: ₹{inv2_total})")

    # 3. Create Invoice 3
    inv3_payload = {
        "customer": {
            "shopName": "Test Customer Gamma",
            "area": "Madhapur Hub"
        },
        "products": [
            {"productName": "Gamma Steel Rod", "quantity": 8, "price": 300.0}
        ]
    }
    r3 = requests.post(f"{BASE_URL}/api/generate-invoice", json=inv3_payload)
    assert r3.status_code == 200, f"Failed to create invoice 3: {r3.text}"
    inv3_data = r3.json()
    assert inv3_data.get('success'), f"Invoice 3 creation unsuccessful: {inv3_data}"
    inv3_num = inv3_data['invoice_number']
    r_inv3_get = requests.get(f"{BASE_URL}/api/invoices/{inv3_num}").json()
    inv3_total = r_inv3_get['invoice']['totalAmount']
    print(f"Created Invoice 3: {inv3_num} (Total: ₹{inv3_total})")

    time.sleep(0.5)

    # 4. Test GET single invoice details (modal preview endpoint)
    print("\n--- Test GET /api/invoices/<invoice_id> for Single Delete Modal ---")
    r_detail = requests.get(f"{BASE_URL}/api/invoices/{inv1_num}")
    assert r_detail.status_code == 200, f"Failed to get invoice detail: {r_detail.text}"
    detail_data = r_detail.json()
    assert detail_data.get('success') is True
    inv_obj = detail_data.get('invoice', {})
    assert inv_obj.get('invoiceNumber') == inv1_num
    assert inv_obj.get('customerName') == "Test Customer Alpha"
    assert inv_obj.get('totalAmount') == inv1_total
    assert inv_obj.get('date') != ""
    print(f"Verified GET invoice details for modal: {inv_obj['invoiceNumber']}, Customer: {inv_obj['customerName']}, Date: {inv_obj.get('dateFormatted') or inv_obj.get('date')}, Amount: ₹{inv_obj['totalAmount']}")

    # 5. Check Dashboard totals BEFORE deleting invoice 1
    dash_before = requests.get(f"{BASE_URL}/api/dashboard?range=all").json()
    invoices_before = dash_before['metrics']['totalInvoices']
    revenue_before = dash_before['metrics']['totalRevenue']
    print(f"\nDashboard before single delete: Invoices={invoices_before}, Revenue=₹{revenue_before}")

    # 6. Test Single Invoice Deletion: DELETE /api/invoices/<invoice_id>
    print(f"\n--- Test Single Invoice Deletion: DELETE /api/invoices/{inv1_num} ---")
    r_del = requests.delete(f"{BASE_URL}/api/invoices/{inv1_num}")
    assert r_del.status_code == 200, f"Failed to delete invoice: {r_del.text}"
    del_res = r_del.json()
    assert del_res.get('success') is True
    print(f"Delete response: {del_res}")

    # Verify invoice 1 is no longer found
    r_get_deleted = requests.get(f"{BASE_URL}/api/invoices/{inv1_num}")
    assert r_get_deleted.status_code == 404, f"Expected 404 for deleted invoice, got {r_get_deleted.status_code}"
    print("Verified deleted invoice returns 404 Not Found.")

    # Verify invoice 2 and 3 still exist (deleting one does NOT delete others)
    r_get_inv2 = requests.get(f"{BASE_URL}/api/invoices/{inv2_num}")
    assert r_get_inv2.status_code == 200
    r_get_inv3 = requests.get(f"{BASE_URL}/api/invoices/{inv3_num}")
    assert r_get_inv3.status_code == 200
    print("Verified remaining invoices (Invoice 2 and 3) are untouched.")

    # Check Dashboard totals AFTER single delete
    dash_after = requests.get(f"{BASE_URL}/api/dashboard?range=all").json()
    invoices_after = dash_after['metrics']['totalInvoices']
    revenue_after = dash_after['metrics']['totalRevenue']
    print(f"Dashboard after single delete: Invoices={invoices_after}, Revenue=₹{revenue_after}")
    assert invoices_after == invoices_before - 1, f"Expected {invoices_before - 1}, got {invoices_after}"
    assert round(revenue_after, 2) == round(revenue_before - inv1_total, 2)
    print("Verified Dashboard statistics updated accurately.")

    # 7. Test Bulk Invoice Deletion: POST /api/invoices/bulk-delete with { "invoiceIds": [...] }
    print(f"\n--- Test Bulk Invoice Deletion: POST /api/invoices/bulk-delete with invoiceIds ---")
    bulk_payload = {
        "invoiceIds": [inv2_num, inv3_num]
    }
    r_bulk = requests.post(f"{BASE_URL}/api/invoices/bulk-delete", json=bulk_payload)
    assert r_bulk.status_code == 200, f"Bulk delete failed: {r_bulk.text}"
    bulk_res = r_bulk.json()
    assert bulk_res.get('success') is True
    assert bulk_res.get('deletedCount') == 2
    assert inv2_num in bulk_res.get('deletedInvoices', [])
    assert inv3_num in bulk_res.get('deletedInvoices', [])
    expected_bulk_total = round(inv2_total + inv3_total, 2)
    assert round(bulk_res.get('totalAmount', 0), 2) == expected_bulk_total
    print(f"Bulk delete response: {bulk_res}")

    # Verify both deleted invoices return 404
    assert requests.get(f"{BASE_URL}/api/invoices/{inv2_num}").status_code == 404
    assert requests.get(f"{BASE_URL}/api/invoices/{inv3_num}").status_code == 404
    print("Verified all bulk deleted invoices return 404 Not Found.")

    # Check Dashboard totals AFTER bulk delete
    dash_bulk_after = requests.get(f"{BASE_URL}/api/dashboard?range=all").json()
    invoices_bulk_after = dash_bulk_after['metrics']['totalInvoices']
    revenue_bulk_after = dash_bulk_after['metrics']['totalRevenue']
    print(f"Dashboard after bulk delete: Invoices={invoices_bulk_after}, Revenue=₹{revenue_bulk_after}")
    assert invoices_bulk_after == invoices_after - 2
    assert round(revenue_bulk_after, 2) == round(revenue_after - expected_bulk_total, 2)
    print("Verified Dashboard statistics accurately subtracted bulk deleted amounts.")

    # 8. Test Error Handling
    print("\n--- Test Error Handling ---")
    # A. Delete non-existent invoice
    r_err1 = requests.delete(f"{BASE_URL}/api/invoices/INV-NON-EXISTENT-999")
    assert r_err1.status_code == 404
    assert "error" in r_err1.json()
    print("Verified 404 with error message for non-existent invoice delete.")

    # B. Directory traversal attempt
    r_err2 = requests.delete(f"{BASE_URL}/api/invoices/..%2Fapp.py")
    assert r_err2.status_code in (400, 404)
    print("Verified path traversal protection on single delete.")

    # C. Bulk delete with invalid/empty list
    r_err3 = requests.post(f"{BASE_URL}/api/invoices/bulk-delete", json={"invoiceIds": []})
    assert r_err3.status_code == 400
    assert "error" in r_err3.json()
    print("Verified 400 with error message for empty bulk delete list.")

    # D. Bulk delete with invalid ID format
    r_err4 = requests.post(f"{BASE_URL}/api/invoices/bulk-delete", json={"invoiceIds": ["../../secret.txt"]})
    assert r_err4.status_code == 400
    print("Verified 400 rejection of directory traversal in bulk delete.")

    print("\n==================================================")
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    test_delete_features()
