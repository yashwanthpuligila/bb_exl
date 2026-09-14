import urllib.request
import urllib.parse
import json
import sqlite3
from pathlib import Path

BASE_URL = "http://127.0.0.1:5000"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "web" / "invoice_learning.db"
STORAGE_DIR = PROJECT_ROOT / "Invoice Storage"

def make_req(endpoint, method="GET", data=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        err_content = err.read().decode("utf-8")
        print(f"HTTP ERROR {err.code} on {method} {endpoint}: {err_content}")
        raise err

def test_full_edit_flow():
    print("=== STARTING EDIT INVOICE E2E VERIFICATION ===")

    # Step 1: Check existing invoices or create a fresh test invoice
    inv_list = make_req("/api/invoices")
    invoices = inv_list.get("invoices", [])
    print(f"Found {len(invoices)} existing invoices in DB.")

    # Create dedicated invoice for testing
    create_payload = {
        "customer": {
            "shopName": "Original Test Shop",
            "area": "Secunderabad"
        },
        "products": [
            {"name": "Brass Ball Valve 1/2", "quantity": 2, "price": 120.0, "total": 240.0},
            {"name": "CPVC Pipe 1 inch", "quantity": 10, "price": 45.0, "total": 450.0}
        ],
        "invoiceType": "current"
    }
    created = make_req("/api/generate-invoice", method="POST", data=create_payload)
    assert created.get("success"), f"Invoice creation failed: {created}"
    test_inv_num = created.get("invoice_number") or created.get("invoiceNumber")
    assert test_inv_num, f"No invoice number returned: {created}"
    print(f"✅ Created test invoice: {test_inv_num}")

    # Check that file exists in Original Test Shop folder
    orig_folder = STORAGE_DIR / "Original Test Shop"
    orig_files = list(orig_folder.glob(f"*{test_inv_num}*"))
    print(f"Original files created: {[f.name for f in orig_files]}")
    assert len(orig_files) > 0, "Original Excel file was not found in customer folder!"

    # Step 2: GET /api/invoices/<invoice_number>
    detail = make_req(f"/api/invoices/{urllib.parse.quote(test_inv_num)}")
    assert detail.get("success"), f"Fetch invoice detail failed: {detail}"
    inv_obj = detail["invoice"]
    assert inv_obj["invoiceNumber"] == test_inv_num
    assert inv_obj["customerName"] == "Original Test Shop"
    assert inv_obj["area"] == "Secunderabad"
    assert len(inv_obj["products"]) == 2
    assert inv_obj["totalAmount"] == 690.0
    print("✅ GET /api/invoices/<inv_num> returns full detail accurately.")

    # Step 3: Test editing quantity & price on existing items
    edit_payload_1 = {
        "customerName": "Original Test Shop",
        "area": "Secunderabad",
        "invoiceType": "current",
        "products": [
            {"name": "Brass Ball Valve 1/2", "quantity": 5, "price": 130.0, "total": 650.0}, # qty 2->5, price 120->130
            {"name": "CPVC Pipe 1 inch", "quantity": 8, "price": 50.0, "total": 400.0}       # qty 10->8, price 45->50
        ]
    }
    res_edit_1 = make_req(f"/api/invoices/{urllib.parse.quote(test_inv_num)}", method="PUT", data=edit_payload_1)
    assert res_edit_1.get("success"), f"Edit 1 failed: {res_edit_1}"
    print(f"✅ PUT edit 1 (quantity & price updates) succeeded: {res_edit_1['message']}")

    # Check updated total
    detail_1 = make_req(f"/api/invoices/{urllib.parse.quote(test_inv_num)}")
    assert detail_1["invoice"]["totalAmount"] == 1050.0, f"Expected total 1050.0, got {detail_1['invoice']['totalAmount']}"
    assert detail_1["invoice"]["invoiceNumber"] == test_inv_num, "Invoice number changed unexpectedly!"
    print("✅ Total recalculated correctly (5*130 + 8*50 = 1050.0). Invoice number strictly preserved.")

    # Step 4: Test adding a product and removing a product
    edit_payload_2 = {
        "customerName": "Original Test Shop",
        "area": "Secunderabad West", # Also updating area
        "invoiceType": "current",
        "products": [
            {"name": "Brass Ball Valve 1/2", "quantity": 5, "price": 130.0, "total": 650.0},
            # Removed CPVC Pipe 1 inch
            {"name": "Teflon Tape Heavy", "quantity": 20, "price": 15.0, "total": 300.0} # Newly added product
        ]
    }
    res_edit_2 = make_req(f"/api/invoices/{urllib.parse.quote(test_inv_num)}", method="PUT", data=edit_payload_2)
    assert res_edit_2.get("success"), f"Edit 2 failed: {res_edit_2}"
    print("✅ PUT edit 2 (add/remove product + update area) succeeded.")

    detail_2 = make_req(f"/api/invoices/{urllib.parse.quote(test_inv_num)}")
    assert detail_2["invoice"]["area"] == "Secunderabad West"
    assert len(detail_2["invoice"]["products"]) == 2
    prod_names = [p["name"] for p in detail_2["invoice"]["products"]]
    assert "CPVC Pipe 1 inch" not in prod_names, "Removed product still present!"
    assert "Teflon Tape Heavy" in prod_names, "Added product missing!"
    assert detail_2["invoice"]["totalAmount"] == 950.0, f"Expected 950.0, got {detail_2['invoice']['totalAmount']}"
    print("✅ Products list and area updated accurately in DB.")

    # Step 5: Test changing Customer Name and verifying folder relocation
    edit_payload_3 = {
        "customerName": "Updated Relocated Mart",
        "area": "Gachibowli",
        "invoiceType": "current",
        "products": [
            {"name": "Brass Ball Valve 1/2", "quantity": 5, "price": 130.0, "total": 650.0},
            {"name": "Teflon Tape Heavy", "quantity": 20, "price": 15.0, "total": 300.0}
        ]
    }
    res_edit_3 = make_req(f"/api/invoices/{urllib.parse.quote(test_inv_num)}", method="PUT", data=edit_payload_3)
    assert res_edit_3.get("success"), f"Edit 3 failed: {res_edit_3}"
    print("✅ PUT edit 3 (customer rename) succeeded.")

    # Verify old files in Original Test Shop were cleaned up
    old_remaining = list(orig_folder.glob(f"*{test_inv_num}*"))
    print(f"Remaining in old folder: {[f.name for f in old_remaining]}")
    assert len(old_remaining) == 0, f"Old customer folder still has files: {old_remaining}"

    # Verify new files in Updated Relocated Mart exist
    new_folder = STORAGE_DIR / "Updated Relocated Mart"
    new_files = list(new_folder.glob(f"*{test_inv_num}*"))
    print(f"Files in new customer folder: {[f.name for f in new_files]}")
    assert len(new_files) > 0, "New customer folder does not contain regenerated invoice file!"

    # Step 6: Verify SQLite DB tables: invoice_edit_history and updated_at
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT invoice_number, customer_display, total_amount, updated_at FROM invoices WHERE invoice_number = ?", (test_inv_num,))
    inv_row = c.fetchone()
    print(f"DB invoices row: {inv_row}")
    assert inv_row is not None
    assert inv_row[1] == "Updated Relocated Mart"
    assert inv_row[2] == 950.0
    assert inv_row[3] is not None, "updated_at timestamp was not set!"

    c.execute("SELECT id, invoice_number, changes_summary, new_total, new_customer FROM invoice_edit_history WHERE invoice_number = ? ORDER BY id ASC", (test_inv_num,))
    history_rows = c.fetchall()
    print(f"DB edit history records ({len(history_rows)}):")
    for r in history_rows:
        print("   -", r)
    assert len(history_rows) == 3, f"Expected 3 history entries, found {len(history_rows)}"
    conn.close()
    print("✅ Audit log history table contains all 3 edit logs.")

    # Step 7: Clean up test invoice using DELETE endpoint
    del_res = make_req(f"/api/invoices/{urllib.parse.quote(test_inv_num)}", method="DELETE")
    assert del_res.get("success"), f"Cleanup failed: {del_res}"
    print(f"✅ Cleaned up test invoice {test_inv_num}.")

    # If new_folder is empty, clean it up
    if new_folder.exists() and not list(new_folder.iterdir()):
        new_folder.rmdir()
    if orig_folder.exists() and not list(orig_folder.iterdir()):
        orig_folder.rmdir()

    print("=== ALL 10 EDIT INVOICE TEST CASES PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_full_edit_flow()
