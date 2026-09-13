import requests
from pathlib import Path
import time

BASE_URL = "http://127.0.0.1:5000"
STORAGE_DIR = Path("Invoice Storage").resolve()

def test_file_cleanup_on_disk():
    print("Testing File Cleanup on Disk...")
    payload = {
        "customer": {
            "shopName": "File Check Cust",
            "area": "Disk Verification Area"
        },
        "products": [
            {"productName": "Disk Pipe Check", "quantity": 2, "price": 99.0}
        ]
    }
    r = requests.post(f"{BASE_URL}/api/generate-invoice", json=payload)
    assert r.status_code == 200
    data = r.json()
    inv_num = data['invoice_number']
    fname = data['filename']
    print(f"Created invoice {inv_num} with file {fname}")

    # Verify file exists on disk
    customer_folder = STORAGE_DIR / "File Check Cust"
    file_path = customer_folder / fname
    assert file_path.exists(), f"Expected file {file_path} to exist on disk before deletion"
    print(f"Verified file exists on disk: {file_path}")

    # Also create a dummy PDF file with the same stem to verify PDF cleanup
    pdf_path = file_path.with_suffix(".pdf")
    pdf_path.write_text("Dummy PDF content for testing cleanup")
    assert pdf_path.exists(), "PDF should exist"
    print(f"Created simulated PDF alongside invoice: {pdf_path}")

    time.sleep(0.5)

    # Now DELETE the invoice via DELETE /api/invoices/<inv_num>
    r_del = requests.delete(f"{BASE_URL}/api/invoices/{inv_num}")
    assert r_del.status_code == 200
    print(f"Invoice {inv_num} deleted via API.")

    time.sleep(0.5)

    # Verify BOTH Excel and PDF files were deleted from disk
    assert not file_path.exists(), f"Excel file {file_path} should have been deleted from disk!"
    assert not pdf_path.exists(), f"PDF file {pdf_path} should have been deleted from disk!"
    print("SUCCESS: Both Excel and PDF files were safely and completely removed from disk!")

if __name__ == "__main__":
    test_file_cleanup_on_disk()
