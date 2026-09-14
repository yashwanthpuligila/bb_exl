"""
Database Viewer Utility for Invoice ERP
Displays summary, customers, invoices, and products from SQLite database.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "web" / "invoice_learning.db"

def show_database():
    if not DB_PATH.exists():
        print(f"❌ Database not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 78)
    print("📊 SRI LAXMI GAYATRI TRADERS - DATABASE VIEWER")
    print(f"📁 Database Path: {DB_PATH}")
    print("=" * 78)

    # Summary Counts
    cust_count = cursor.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    inv_count = cursor.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    prod_count = cursor.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    total_sales = cursor.execute("SELECT COALESCE(SUM(total_amount), 0) FROM invoices").fetchone()[0]

    print("\n📈 SUMMARY STATS:")
    print(f"   • Total Customers : {cust_count}")
    print(f"   • Total Invoices  : {inv_count}")
    print(f"   • Total Products  : {prod_count}")
    print(f"   • Total Sales     : ₹{total_sales:,.2f}")

    # Registered Customers
    print("\n" + "-" * 78)
    print("👥 REGISTERED CUSTOMERS:")
    print("-" * 78)
    print(f"{'Customer Name':<30} {'Area':<20} {'Times Invoiced':<15} {'Last Invoiced':<12}")
    print("-" * 78)
    for row in cursor.execute("SELECT display_name, area, usage_count, last_used_date FROM customers ORDER BY usage_count DESC, id DESC LIMIT 15"):
        name = (row['display_name'] or '')[:28]
        area = (row['area'] or '')[:18]
        usage = row['usage_count'] or 0
        last_date = str(row['last_used_date'] or '')[:10]
        print(f"{name:<30} {area:<20} {usage:<15} {last_date:<12}")

    # Recent Invoices
    print("\n" + "-" * 78)
    print("📑 RECENT INVOICES:")
    print("-" * 78)
    print(f"{'Invoice Number':<26} {'Date':<12} {'Customer':<22} {'Amount (₹)':<14}")
    print("-" * 78)
    for row in cursor.execute("SELECT invoice_number, invoice_date, customer_display, total_amount FROM invoices ORDER BY id DESC LIMIT 10"):
        num = (row['invoice_number'] or '')[:24]
        date = str(row['invoice_date'] or '')[:10]
        cust = (row['customer_display'] or '')[:20]
        amt = row['total_amount'] or 0.0
        print(f"{num:<26} {date:<12} {cust:<22} ₹{amt:<13,.2f}")

    # Top Products
    print("\n" + "-" * 78)
    print("📦 PRODUCTS LIST (Top by Usage / Latest Price):")
    print("-" * 78)
    print(f"{'Product Name':<35} {'Latest Price':<15} {'Times Ordered':<15}")
    print("-" * 78)
    for row in cursor.execute("SELECT display_name, latest_price, usage_count FROM products ORDER BY usage_count DESC, id DESC LIMIT 15"):
        pname = (row['display_name'] or '')[:33]
        price = row['latest_price'] or 0.0
        porders = row['usage_count'] or 0
        print(f"{pname:<35} ₹{price:<14,.2f} {porders:<15}")

    print("\n" + "=" * 78)

if __name__ == "__main__":
    show_database()
