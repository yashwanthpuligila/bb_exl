#!/usr/bin/env python3
"""
SQLite to Render PostgreSQL Data Migration Script
Transfers all existing invoice, customer, product, and purchase records
from local SQLite (invoice_learning.db) to Render PostgreSQL.

Features:
- Preserves primary key IDs, timestamps, invoice numbers, totals, and line item orders
- Synchronizes PostgreSQL auto-increment sequences (setval)
- Performs automatic row count verification between SQLite and PostgreSQL
- Safe and repeatable (uses ON CONFLICT clauses; never modifies source SQLite database)
"""

import sys
import os
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime

try:
    import psycopg2
    from psycopg2.extras import DictCursor
except ImportError:
    print("❌ Error: psycopg2 is not installed. Please run: pip install psycopg2-binary")
    sys.exit(1)

# Default path to SQLite database
DEFAULT_SQLITE_PATH = Path(__file__).resolve().parent / "web" / "invoice_learning.db"

POSTGRES_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    normalized_name TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    area TEXT NOT NULL,
    usage_count INTEGER DEFAULT 1,
    last_used_date TIMESTAMP NOT NULL,
    recent_invoice_number TEXT
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    normalized_name TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    latest_price REAL NOT NULL,
    usage_count INTEGER DEFAULT 1,
    last_used_date TIMESTAMP NOT NULL,
    recent_invoice_number TEXT
);

CREATE TABLE IF NOT EXISTS customer_purchases (
    id SERIAL PRIMARY KEY,
    customer_norm TEXT NOT NULL,
    customer_display TEXT NOT NULL,
    product_norm TEXT NOT NULL,
    product_display TEXT NOT NULL,
    order_count INTEGER DEFAULT 1,
    total_quantity REAL DEFAULT 0,
    last_price REAL NOT NULL,
    last_ordered_date TIMESTAMP NOT NULL,
    recent_invoice_number TEXT,
    CONSTRAINT uq_cp_customer_product UNIQUE(customer_norm, product_norm)
);

CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    invoice_number TEXT UNIQUE NOT NULL,
    customer_norm TEXT NOT NULL,
    customer_display TEXT NOT NULL,
    area TEXT NOT NULL,
    invoice_date TIMESTAMP NOT NULL,
    invoice_type TEXT NOT NULL,
    product_count INTEGER NOT NULL,
    total_quantity REAL NOT NULL,
    total_amount REAL NOT NULL,
    file_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP,
    extra_charges_desc TEXT,
    extra_charges_amount REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS invoice_items (
    id SERIAL PRIMARY KEY,
    invoice_number TEXT NOT NULL,
    customer_norm TEXT NOT NULL,
    product_norm TEXT NOT NULL,
    product_display TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    total_amount REAL NOT NULL,
    item_order INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS processed_invoices (
    invoice_file TEXT UNIQUE NOT NULL,
    customer_norm TEXT NOT NULL,
    processed_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS invoice_edit_history (
    id SERIAL PRIMARY KEY,
    invoice_number TEXT NOT NULL,
    edited_at TIMESTAMP NOT NULL,
    old_customer TEXT,
    new_customer TEXT,
    old_total REAL,
    new_total REAL,
    changes_summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_customer_norm ON customers(normalized_name);
CREATE INDEX IF NOT EXISTS idx_customer_rank ON customers(usage_count DESC, last_used_date DESC);
CREATE INDEX IF NOT EXISTS idx_product_norm ON products(normalized_name);
CREATE INDEX IF NOT EXISTS idx_product_rank ON products(usage_count DESC, last_used_date DESC);
CREATE INDEX IF NOT EXISTS idx_cp_cust ON customer_purchases(customer_norm);
CREATE INDEX IF NOT EXISTS idx_cp_order_count ON customer_purchases(customer_norm, order_count DESC);
CREATE INDEX IF NOT EXISTS idx_inv_num ON invoices(invoice_number);
CREATE INDEX IF NOT EXISTS idx_inv_cust ON invoices(customer_norm);
CREATE INDEX IF NOT EXISTS idx_inv_date ON invoices(invoice_date DESC);
CREATE INDEX IF NOT EXISTS idx_inv_amt ON invoices(total_amount DESC);
CREATE INDEX IF NOT EXISTS idx_item_inv ON invoice_items(invoice_number);
CREATE INDEX IF NOT EXISTS idx_item_prod ON invoice_items(product_norm);
"""

def clean_postgres_url(url: str) -> str:
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url

def migrate(sqlite_path: Path, pg_url: str, clean_target: bool = False):
    if not sqlite_path.exists():
        print(f"❌ Error: SQLite source database not found at: {sqlite_path}")
        sys.exit(1)

    pg_url = clean_postgres_url(pg_url)

    print("=" * 60)
    print("🚀 SQLite → Render PostgreSQL Migration")
    print("=" * 60)
    print(f"📂 Source SQLite DB : {sqlite_path}")
    masked_url = pg_url.split("@")[-1] if "@" in pg_url else "configured target"
    print(f"☁️ Target PostgreSQL: ...@{masked_url}")
    print()

    # 1. Connect to SQLite
    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    # 2. Connect to PostgreSQL
    try:
        pg_conn = psycopg2.connect(pg_url)
        pg_cur = pg_conn.cursor()
    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")
        print("\nPlease check your DATABASE_URL or network connection.")
        sys.exit(1)

    try:
        # 3. Create tables and schema in PostgreSQL
        print("🔧 Creating PostgreSQL tables and indexes...")
        pg_cur.execute(POSTGRES_SCHEMA_DDL)
        pg_conn.commit()

        if clean_target:
            print("⚠️ Clean target requested: Truncating existing PostgreSQL tables...")
            pg_cur.execute("""
                TRUNCATE TABLE invoice_items, invoices, customer_purchases,
                customers, products, processed_invoices, invoice_edit_history CASCADE;
            """)
            pg_conn.commit()

        # 4. Migrate Customers
        print("📦 Migrating customers...")
        sqlite_cur.execute("SELECT id, normalized_name, display_name, area, usage_count, last_used_date, recent_invoice_number FROM customers ORDER BY id ASC")
        customers = sqlite_cur.fetchall()
        for r in customers:
            pg_cur.execute("""
                INSERT INTO customers (id, normalized_name, display_name, area, usage_count, last_used_date, recent_invoice_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (normalized_name) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    area = EXCLUDED.area,
                    usage_count = EXCLUDED.usage_count,
                    last_used_date = EXCLUDED.last_used_date,
                    recent_invoice_number = EXCLUDED.recent_invoice_number
            """, (r['id'], r['normalized_name'], r['display_name'], r['area'], r['usage_count'], r['last_used_date'], r['recent_invoice_number']))
        pg_conn.commit()

        # 5. Migrate Products
        print("📦 Migrating products...")
        sqlite_cur.execute("SELECT id, normalized_name, display_name, latest_price, usage_count, last_used_date, recent_invoice_number FROM products ORDER BY id ASC")
        products = sqlite_cur.fetchall()
        for r in products:
            pg_cur.execute("""
                INSERT INTO products (id, normalized_name, display_name, latest_price, usage_count, last_used_date, recent_invoice_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (normalized_name) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    latest_price = EXCLUDED.latest_price,
                    usage_count = EXCLUDED.usage_count,
                    last_used_date = EXCLUDED.last_used_date,
                    recent_invoice_number = EXCLUDED.recent_invoice_number
            """, (r['id'], r['normalized_name'], r['display_name'], r['latest_price'], r['usage_count'], r['last_used_date'], r['recent_invoice_number']))
        pg_conn.commit()

        # 6. Migrate Customer Purchases
        print("📦 Migrating customer_purchases...")
        sqlite_cur.execute("SELECT id, customer_norm, customer_display, product_norm, product_display, order_count, total_quantity, last_price, last_ordered_date, recent_invoice_number FROM customer_purchases ORDER BY id ASC")
        purchases = sqlite_cur.fetchall()
        for r in purchases:
            pg_cur.execute("""
                INSERT INTO customer_purchases (id, customer_norm, customer_display, product_norm, product_display, order_count, total_quantity, last_price, last_ordered_date, recent_invoice_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (customer_norm, product_norm) DO UPDATE SET
                    order_count = EXCLUDED.order_count,
                    total_quantity = EXCLUDED.total_quantity,
                    last_price = EXCLUDED.last_price,
                    last_ordered_date = EXCLUDED.last_ordered_date,
                    recent_invoice_number = EXCLUDED.recent_invoice_number,
                    customer_display = EXCLUDED.customer_display,
                    product_display = EXCLUDED.product_display
            """, (r['id'], r['customer_norm'], r['customer_display'], r['product_norm'], r['product_display'], r['order_count'], r['total_quantity'], r['last_price'], r['last_ordered_date'], r['recent_invoice_number']))
        pg_conn.commit()

        # 7. Migrate Invoices
        print("📦 Migrating invoices...")
        sqlite_cur.execute("""
            SELECT id, invoice_number, customer_norm, customer_display, area,
                   invoice_date, invoice_type, product_count, total_quantity,
                   total_amount, file_path, filename, created_at,
                   updated_at, extra_charges_desc, extra_charges_amount
            FROM invoices ORDER BY id ASC
        """)
        invoices = sqlite_cur.fetchall()
        for r in invoices:
            pg_cur.execute("""
                INSERT INTO invoices (
                    id, invoice_number, customer_norm, customer_display, area,
                    invoice_date, invoice_type, product_count, total_quantity,
                    total_amount, file_path, filename, created_at,
                    updated_at, extra_charges_desc, extra_charges_amount
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (invoice_number) DO UPDATE SET
                    customer_norm = EXCLUDED.customer_norm,
                    customer_display = EXCLUDED.customer_display,
                    area = EXCLUDED.area,
                    invoice_date = EXCLUDED.invoice_date,
                    invoice_type = EXCLUDED.invoice_type,
                    product_count = EXCLUDED.product_count,
                    total_quantity = EXCLUDED.total_quantity,
                    total_amount = EXCLUDED.total_amount,
                    file_path = EXCLUDED.file_path,
                    filename = EXCLUDED.filename,
                    created_at = EXCLUDED.created_at,
                    updated_at = EXCLUDED.updated_at,
                    extra_charges_desc = EXCLUDED.extra_charges_desc,
                    extra_charges_amount = EXCLUDED.extra_charges_amount
            """, (
                r['id'], r['invoice_number'], r['customer_norm'], r['customer_display'], r['area'],
                r['invoice_date'], r['invoice_type'], r['product_count'], r['total_quantity'],
                r['total_amount'], r['file_path'], r['filename'], r['created_at'],
                r['updated_at'], r['extra_charges_desc'], r['extra_charges_amount']
            ))
        pg_conn.commit()

        # 8. Migrate Invoice Items
        print("📦 Migrating invoice_items...")
        sqlite_cur.execute("""
            SELECT id, invoice_number, customer_norm, product_norm, product_display,
                   quantity, price, total_amount, item_order
            FROM invoice_items ORDER BY id ASC
        """)
        items = sqlite_cur.fetchall()
        for r in items:
            pg_cur.execute("""
                INSERT INTO invoice_items (id, invoice_number, customer_norm, product_norm, product_display, quantity, price, total_amount, item_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    invoice_number = EXCLUDED.invoice_number,
                    customer_norm = EXCLUDED.customer_norm,
                    product_norm = EXCLUDED.product_norm,
                    product_display = EXCLUDED.product_display,
                    quantity = EXCLUDED.quantity,
                    price = EXCLUDED.price,
                    total_amount = EXCLUDED.total_amount,
                    item_order = EXCLUDED.item_order
            """, (r['id'], r['invoice_number'], r['customer_norm'], r['product_norm'], r['product_display'], r['quantity'], r['price'], r['total_amount'], r['item_order']))
        pg_conn.commit()

        # 9. Migrate Processed Invoices
        print("📦 Migrating processed_invoices...")
        sqlite_cur.execute("SELECT invoice_file, customer_norm, processed_at FROM processed_invoices")
        processed = sqlite_cur.fetchall()
        for r in processed:
            pg_cur.execute("""
                INSERT INTO processed_invoices (invoice_file, customer_norm, processed_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (invoice_file) DO UPDATE SET
                    customer_norm = EXCLUDED.customer_norm,
                    processed_at = EXCLUDED.processed_at
            """, (r['invoice_file'], r['customer_norm'], r['processed_at']))
        pg_conn.commit()

        # 10. Migrate Invoice Edit History
        print("📦 Migrating invoice_edit_history...")
        sqlite_cur.execute("SELECT id, invoice_number, edited_at, old_customer, new_customer, old_total, new_total, changes_summary FROM invoice_edit_history ORDER BY id ASC")
        edits = sqlite_cur.fetchall()
        for r in edits:
            pg_cur.execute("""
                INSERT INTO invoice_edit_history (id, invoice_number, edited_at, old_customer, new_customer, old_total, new_total, changes_summary)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    invoice_number = EXCLUDED.invoice_number,
                    edited_at = EXCLUDED.edited_at,
                    old_customer = EXCLUDED.old_customer,
                    new_customer = EXCLUDED.new_customer,
                    old_total = EXCLUDED.old_total,
                    new_total = EXCLUDED.new_total,
                    changes_summary = EXCLUDED.changes_summary
            """, (r['id'], r['invoice_number'], r['edited_at'], r['old_customer'], r['new_customer'], r['old_total'], r['new_total'], r['changes_summary']))
        pg_conn.commit()

        # 11. Synchronize PostgreSQL auto-increment sequences
        print("🔄 Synchronizing PostgreSQL serial sequences...")
        tables_with_serial = ['customers', 'products', 'customer_purchases', 'invoices', 'invoice_items', 'invoice_edit_history']
        for tbl in tables_with_serial:
            pg_cur.execute(f"""
                SELECT setval(
                    pg_get_serial_sequence('{tbl}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {tbl}), 1)
                );
            """)
        pg_conn.commit()

        # 12. Verification Comparison
        print("\n" + "=" * 60)
        print("SQLite → PostgreSQL Migration")
        print("=" * 60)

        tables_to_verify = [
            'customers',
            'products',
            'invoices',
            'invoice_items',
            'customer_purchases',
            'processed_invoices',
            'invoice_edit_history'
        ]

        all_matched = True
        for tbl in tables_to_verify:
            sqlite_count = sqlite_cur.execute(f'SELECT COUNT(*) FROM "{tbl}"').fetchone()[0]
            pg_cur.execute(f'SELECT COUNT(*) FROM "{tbl}"')
            pg_count = pg_cur.fetchone()[0]

            is_match = (sqlite_count == pg_count)
            mark = "✓" if is_match else "❌ MISMATCH"
            if not is_match:
                all_matched = False

            print(f"\n{tbl}:")
            print(f"SQLite: {sqlite_count}")
            print(f"PostgreSQL: {pg_count} {mark}")

        print("\n" + "=" * 60)
        if all_matched:
            print("✅ MIGRATION SUCCESSFUL! All row counts match perfectly.")
            print("=" * 60)
        else:
            print("❌ MIGRATION FAILED: Some row counts do not match!")
            print("=" * 60)
            sys.exit(1)

    except Exception as err:
        pg_conn.rollback()
        print(f"\n❌ Error during migration: {err}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        sqlite_conn.close()
        pg_conn.close()

def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite database to Render PostgreSQL")
    parser.add_argument(
        "--target-url",
        help="PostgreSQL connection string (defaults to DATABASE_URL environment variable)",
        default=os.environ.get("DATABASE_URL")
    )
    parser.add_argument(
        "--sqlite-path",
        help="Path to SQLite invoice_learning.db file",
        default=str(DEFAULT_SQLITE_PATH)
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean target PostgreSQL tables before importing"
    )

    args = parser.parse_args()

    if not args.target_url:
        print("❌ Error: DATABASE_URL not provided.")
        print("Please set the DATABASE_URL environment variable or pass --target-url 'postgresql://...'")
        print("Example:")
        print('  python migrate_sqlite_to_postgres.py --target-url "postgresql://user:password@hostname/dbname"')
        sys.exit(1)

    migrate(Path(args.sqlite_path), args.target_url, clean_target=args.clean)

if __name__ == "__main__":
    main()
