"""
Database Viewer & Cloud Sync Utility for Invoice ERP
View local database, inspect live Render cloud database, or sync cloud data to PC.
"""
import sqlite3
import urllib.request
import json
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DB_PATH = ROOT_DIR / "web" / "invoice_learning.db"
URL_CONFIG_FILE = ROOT_DIR / "render_url.txt"

def get_saved_render_url():
    if URL_CONFIG_FILE.exists():
        try:
            url = URL_CONFIG_FILE.read_text(encoding="utf-8").strip()
            if url:
                return url
        except Exception:
            pass
    return ""

def save_render_url(url):
    url = url.strip().rstrip("/")
    if url and not url.startswith("http"):
        url = "https://" + url
    try:
        URL_CONFIG_FILE.write_text(url, encoding="utf-8")
    except Exception:
        pass
    return url

def show_local_database():
    if not DB_PATH.exists():
        print(f"❌ Local database not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("\n" + "=" * 78)
    print("📊 LOCAL PC DATABASE (D:\\bb_exl\\web\\invoice_learning.db)")
    print("=" * 78)

    cust_count = cursor.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    inv_count = cursor.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    prod_count = cursor.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    total_sales = cursor.execute("SELECT COALESCE(SUM(total_amount), 0) FROM invoices").fetchone()[0]

    print(f"📈 SUMMARY:")
    print(f"   • Total Customers : {cust_count}")
    print(f"   • Total Invoices  : {inv_count}")
    print(f"   • Total Products  : {prod_count}")
    print(f"   • Total Sales     : ₹{total_sales:,.2f}")

    print("\n👥 REGISTERED CUSTOMERS:")
    print("-" * 78)
    print(f"{'Customer Name':<30} {'Area':<20} {'Times Invoiced':<15} {'Last Invoiced':<12}")
    print("-" * 78)
    for row in cursor.execute("SELECT display_name, area, usage_count, last_used_date FROM customers ORDER BY usage_count DESC, id DESC LIMIT 10"):
        name = (row['display_name'] or '')[:28]
        area = (row['area'] or '')[:18]
        usage = row['usage_count'] or 0
        last_date = str(row['last_used_date'] or '')[:10]
        print(f"{name:<30} {area:<20} {usage:<15} {last_date:<12}")

    print("\n📑 RECENT INVOICES:")
    print("-" * 78)
    print(f"{'Invoice Number':<26} {'Date':<12} {'Customer':<22} {'Amount (₹)':<14}")
    print("-" * 78)
    for row in cursor.execute("SELECT invoice_number, invoice_date, customer_display, total_amount FROM invoices ORDER BY id DESC LIMIT 10"):
        num = (row['invoice_number'] or '')[:24]
        date = str(row['invoice_date'] or '')[:10]
        cust = (row['customer_display'] or '')[:20]
        amt = row['total_amount'] or 0.0
        print(f"{num:<26} {date:<12} {cust:<22} ₹{amt:<13,.2f}")
    print("=" * 78)

def show_cloud_database():
    saved_url = get_saved_render_url()
    prompt = f"Enter your Render URL [{saved_url}]: " if saved_url else "Enter your Render URL (e.g. https://invoice-erp-xxxx.onrender.com): "
    raw_url = input(prompt).strip()
    render_url = raw_url if raw_url else saved_url
    if not render_url:
        print("❌ No Render URL provided.")
        return
    render_url = save_render_url(render_url)

    print(f"\n🌐 Connecting to Cloud Database at: {render_url}...")
    try:
        req = urllib.request.Request(f"{render_url}/api/invoices?limit=15", headers={"User-Agent": "InvoiceViewer/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            
        req_cust = urllib.request.Request(f"{render_url}/api/customers", headers={"User-Agent": "InvoiceViewer/1.0"})
        with urllib.request.urlopen(req_cust, timeout=12) as resp_c:
            cust_data = json.loads(resp_c.read().decode("utf-8"))

        invoices = data.get("invoices", [])
        customers = cust_data.get("customers", [])
        total_sales = sum(inv.get("totalAmount", 0) for inv in invoices)

        print("\n" + "=" * 78)
        print(f"☁️ LIVE CLOUD DATABASE ({render_url})")
        print("=" * 78)
        print(f"📈 SUMMARY:")
        print(f"   • Total Invoices on Cloud  : {len(invoices)}")
        print(f"   • Total Customers on Cloud : {len(customers)}")
        print(f"   • Total Sales on Cloud     : ₹{total_sales:,.2f}")

        print("\n👥 CUSTOMERS ON CLOUD:")
        print("-" * 78)
        print(f"{'Customer Name':<30} {'Area':<20} {'Invoices':<10} {'Total (₹)':<14}")
        print("-" * 78)
        for c in customers[:10]:
            name = (c.get('customerName') or '')[:28]
            area = (c.get('area') or '')[:18]
            inv_c = c.get('invoiceCount', 0)
            tot = c.get('totalAmount', 0.0)
            print(f"{name:<30} {area:<20} {inv_c:<10} ₹{tot:<13,.2f}")

        print("\n📑 RECENT INVOICES ON CLOUD:")
        print("-" * 78)
        print(f"{'Invoice Number':<26} {'Date':<14} {'Customer':<20} {'Amount (₹)':<14}")
        print("-" * 78)
        for inv in invoices[:10]:
            num = (inv.get('invoiceNumber') or '')[:24]
            date = str(inv.get('invoiceDateFormatted') or inv.get('invoiceDate') or '')[:12]
            cust = (inv.get('customerName') or '')[:18]
            amt = inv.get('totalAmount', 0.0)
            print(f"{num:<26} {date:<14} {cust:<20} ₹{amt:<13,.2f}")
        print("=" * 78)

    except Exception as e:
        print(f"❌ Failed to reach cloud database: {e}")
        print("   (Note: If Render was sleeping, it may take 30-40 seconds to wake up. Please try again).")

def sync_cloud_to_local():
    saved_url = get_saved_render_url()
    prompt = f"Enter your Render URL [{saved_url}]: " if saved_url else "Enter your Render URL (e.g. https://invoice-erp-xxxx.onrender.com): "
    raw_url = input(prompt).strip()
    render_url = raw_url if raw_url else saved_url
    if not render_url:
        print("❌ No Render URL provided.")
        return
    render_url = save_render_url(render_url)

    export_url = f"{render_url}/api/admin/export-db"
    print(f"\n📥 Downloading live database from: {export_url}...")

    try:
        req = urllib.request.Request(export_url, headers={"User-Agent": "InvoiceSync/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read()

        if len(content) < 100:
            print("❌ Downloaded file appears too small or invalid.")
            return

        # Backup current local DB before overwriting
        if DB_PATH.exists():
            backup_path = DB_PATH.with_suffix(".db.backup")
            try:
                DB_PATH.rename(backup_path)
            except Exception:
                pass

        DB_PATH.write_bytes(content)
        print("✅ SUCCESS! Cloud database downloaded and synced to your local PC:")
        print(f"   📁 {DB_PATH} ({len(content):,} bytes)")

        # Show updated local database
        show_local_database()

    except Exception as e:
        print(f"❌ Failed to sync from cloud: {e}")
        print("   (Ensure your Render URL is correct and the latest code is deployed on Render).")

def main():
    while True:
        print("\n=======================================================")
        print("       SRI LAXMI GAYATRI TRADERS - DATABASE HUB        ")
        print("=======================================================")
        print("  [1] View Local PC Database")
        print("  [2] View Live Cloud Database (Render URL)")
        print("  [3] Sync & Download Cloud Database to this PC")
        print("  [4] Exit")
        print("-------------------------------------------------------")
        choice = input("Select an option [1-4] (default 1): ").strip()

        if choice in ["", "1"]:
            show_local_database()
        elif choice == "2":
            show_cloud_database()
        elif choice == "3":
            sync_cloud_to_local()
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid choice, please select 1, 2, 3, or 4.")

if __name__ == "__main__":
    main()
