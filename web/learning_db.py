import sqlite3
import os
import re
import math
from pathlib import Path
from datetime import datetime
import openpyxl

DB_PATH = Path(__file__).resolve().parent / "invoice_learning.db"

def get_connection():
    """Get SQLite database connection with row factory."""
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def normalize_text(text: str) -> str:
    """Collapses spaces and converts to lowercase for deduplication and matching."""
    return " ".join(str(text or "").strip().lower().split())

def init_db():
    """Initialize database tables and indexes."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_name TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                area TEXT NOT NULL,
                usage_count INTEGER DEFAULT 1,
                last_used_date TIMESTAMP NOT NULL,
                recent_invoice_number TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_name TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                latest_price REAL NOT NULL,
                usage_count INTEGER DEFAULT 1,
                last_used_date TIMESTAMP NOT NULL,
                recent_invoice_number TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_norm TEXT NOT NULL,
                customer_display TEXT NOT NULL,
                product_norm TEXT NOT NULL,
                product_display TEXT NOT NULL,
                order_count INTEGER DEFAULT 1,
                total_quantity REAL DEFAULT 0,
                last_price REAL NOT NULL,
                last_ordered_date TIMESTAMP NOT NULL,
                recent_invoice_number TEXT,
                UNIQUE(customer_norm, product_norm)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_invoices (
                invoice_file TEXT UNIQUE NOT NULL,
                customer_norm TEXT NOT NULL,
                processed_at TIMESTAMP NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_norm ON customers(normalized_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_rank ON customers(usage_count DESC, last_used_date DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_norm ON products(normalized_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_rank ON products(usage_count DESC, last_used_date DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cp_cust ON customer_purchases(customer_norm)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cp_order_count ON customer_purchases(customer_norm, order_count DESC)")
        conn.commit()

def record_customer(shop_name: str, area: str = "", invoice_number: str = "", date_time: datetime = None):
    """
    Record or update customer usage.
    Deduplicates based on normalized name (case and extra spaces insensitive).
    """
    norm = normalize_text(shop_name)
    if not norm:
        return
    clean_display = " ".join(str(shop_name).strip().split())
    clean_area = " ".join(str(area or "").strip().split())
    if not date_time:
        date_time = datetime.now()
    dt_str = date_time.isoformat()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, usage_count, display_name, area FROM customers WHERE normalized_name = ?", (norm,))
        row = cursor.fetchone()
        if row:
            cid, count, existing_display, existing_area = row
            cursor.execute("""
                UPDATE customers 
                SET usage_count = usage_count + 1,
                    last_used_date = ?,
                    area = CASE WHEN ? != '' THEN ? ELSE area END,
                    display_name = ?,
                    recent_invoice_number = ?
                WHERE id = ?
            """, (dt_str, clean_area, clean_area, clean_display, invoice_number, cid))
        else:
            cursor.execute("""
                INSERT INTO customers (normalized_name, display_name, area, usage_count, last_used_date, recent_invoice_number)
                VALUES (?, ?, ?, 1, ?, ?)
            """, (norm, clean_display, clean_area, dt_str, invoice_number))
        conn.commit()

def record_product(name: str, price: float = 0.0, invoice_number: str = "", date_time: datetime = None):
    """
    Record or update global product usage.
    Deduplicates based on normalized name (case and extra spaces insensitive).
    """
    norm = normalize_text(name)
    if not norm:
        return
    clean_display = " ".join(str(name).strip().split())
    try:
        price_val = float(price)
    except (ValueError, TypeError):
        price_val = 0.0
        
    if not date_time:
        date_time = datetime.now()
    dt_str = date_time.isoformat()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, usage_count FROM products WHERE normalized_name = ?", (norm,))
        row = cursor.fetchone()
        if row:
            pid, count = row
            cursor.execute("""
                UPDATE products
                SET usage_count = usage_count + 1,
                    latest_price = CASE WHEN ? > 0 THEN ? ELSE latest_price END,
                    last_used_date = ?,
                    display_name = ?,
                    recent_invoice_number = ?
                WHERE id = ?
            """, (price_val, price_val, dt_str, clean_display, invoice_number, pid))
        else:
            cursor.execute("""
                INSERT INTO products (normalized_name, display_name, latest_price, usage_count, last_used_date, recent_invoice_number)
                VALUES (?, ?, ?, 1, ?, ?)
            """, (norm, clean_display, price_val, dt_str, invoice_number))
        conn.commit()

def record_customer_purchase(shop_name: str, product_name: str, quantity: float = 1.0, price: float = 0.0, invoice_number: str = "", date_time: datetime = None):
    """
    Record or update customer-specific product purchase history.
    Normalizes both customer and product names for deduplication.
    Tracks order count, total quantity, latest customer-specific price, and last ordered date.
    """
    c_norm = normalize_text(shop_name)
    p_norm = normalize_text(product_name)
    if not c_norm or not p_norm:
        return
        
    c_display = " ".join(str(shop_name).strip().split())
    p_display = " ".join(str(product_name).strip().split())
    try:
        qty = float(quantity) if quantity is not None else 1.0
    except (ValueError, TypeError):
        qty = 1.0
    try:
        price_val = float(price) if price is not None else 0.0
    except (ValueError, TypeError):
        price_val = 0.0
        
    if not date_time:
        date_time = datetime.now()
    dt_str = date_time.isoformat()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, order_count, total_quantity, last_price FROM customer_purchases WHERE customer_norm = ? AND product_norm = ?",
            (c_norm, p_norm)
        )
        row = cursor.fetchone()
        if row:
            cpid, count, existing_qty, existing_price = row
            cursor.execute("""
                UPDATE customer_purchases
                SET order_count = order_count + 1,
                    total_quantity = total_quantity + ?,
                    last_price = CASE WHEN ? > 0 THEN ? ELSE last_price END,
                    last_ordered_date = ?,
                    recent_invoice_number = ?,
                    customer_display = ?,
                    product_display = ?
                WHERE id = ?
            """, (qty, price_val, price_val, dt_str, invoice_number, c_display, p_display, cpid))
        else:
            cursor.execute("""
                INSERT INTO customer_purchases (
                    customer_norm, customer_display, product_norm, product_display,
                    order_count, total_quantity, last_price, last_ordered_date, recent_invoice_number
                ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
            """, (c_norm, c_display, p_norm, p_display, qty, price_val, dt_str, invoice_number))
        conn.commit()

def search_customers(query: str, limit: int = 10):
    """
    Search customer suggestions by prefix / substring.
    Ordered by prefix matches first, then word start, then substring,
    followed by usage_count DESC, then last_used_date DESC.
    """
    norm_q = normalize_text(query)
    if not norm_q:
        return []
        
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT display_name, area, usage_count, last_used_date, recent_invoice_number
            FROM customers
            WHERE normalized_name LIKE ?
            ORDER BY
                CASE 
                    WHEN normalized_name LIKE ? THEN 0 
                    WHEN normalized_name LIKE ? THEN 1 
                    ELSE 2 
                END,
                usage_count DESC,
                last_used_date DESC
            LIMIT ?
        """, (f"%{norm_q}%", f"{norm_q}%", f"% {norm_q}%", limit))
        rows = cursor.fetchall()
        
        results = []
        for r in rows:
            results.append({
                "shopName": r[0],
                "area": r[1],
                "usageCount": r[2],
                "lastUsed": r[3],
                "recentInvoice": r[4]
            })
        return results

def search_products(query: str, limit: int = 10):
    """
    Search product suggestions by prefix / substring.
    Ordered by prefix matches first, then word start, then substring,
    followed by usage_count DESC, then last_used_date DESC.
    """
    norm_q = normalize_text(query)
    if not norm_q:
        return []
        
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT display_name, latest_price, usage_count, last_used_date, recent_invoice_number
            FROM products
            WHERE normalized_name LIKE ?
            ORDER BY
                CASE 
                    WHEN normalized_name LIKE ? THEN 0 
                    WHEN normalized_name LIKE ? THEN 1 
                    ELSE 2 
                END,
                usage_count DESC,
                last_used_date DESC
            LIMIT ?
        """, (f"%{norm_q}%", f"{norm_q}%", f"% {norm_q}%", limit))
        rows = cursor.fetchall()
        
        results = []
        for r in rows:
            results.append({
                "name": r[0],
                "price": r[1],
                "usageCount": r[2],
                "lastUsed": r[3],
                "recentInvoice": r[4]
            })
        return results

def format_relative_date(dt_str: str) -> str:
    """Helper to convert ISO timestamp to friendly relative date string."""
    try:
        dt = datetime.fromisoformat(str(dt_str).replace("Z", ""))
        diff = datetime.now() - dt
        days = diff.days
        if days <= 0:
            return "Today"
        elif days == 1:
            return "Yesterday"
        elif days < 30:
            return f"{days} days ago"
        elif days < 365:
            months = max(1, days // 30)
            return f"{months} {'month' if months == 1 else 'months'} ago"
        else:
            years = max(1, days // 365)
            return f"{years} {'year' if years == 1 else 'years'} ago"
    except Exception:
        return ""

def get_customer_recommendations(shop_name: str, limit: int = 8):
    """
    Calculates product recommendations strictly based on this customer's own order history.
    Ranks products based on:
      1. Order count (how many times customer purchased this product)
      2. Total quantity purchased
      3. Recency of purchase (recent orders weighted higher than old ones)
      4. Most recently charged price to this specific customer
    """
    init_db()
    c_norm = normalize_text(shop_name)
    clean_name = " ".join(str(shop_name or "").strip().split())
    
    if not c_norm:
        return {
            "hasHistory": False,
            "customer": clean_name or "Selected Customer",
            "recommendations": [],
            "popularProducts": get_popular_products(limit=5)
        }
        
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT product_display, order_count, total_quantity, last_price, last_ordered_date, recent_invoice_number
            FROM customer_purchases
            WHERE customer_norm = ?
        """, (c_norm,))
        rows = cursor.fetchall()
        
        if not rows:
            return {
                "hasHistory": False,
                "customer": clean_name,
                "recommendations": [],
                "popularProducts": get_popular_products(limit=5)
            }
            
        now = datetime.now()
        scored_items = []
        for r in rows:
            p_display, order_count, total_qty, last_price, last_date_str, recent_inv = r
            try:
                order_dt = datetime.fromisoformat(str(last_date_str).replace("Z", ""))
                days_ago = max(0.0, (now - order_dt).total_seconds() / 86400.0)
            except Exception:
                days_ago = 30.0
                
            # Recency factor: gently decays over 60 days
            recency_weight = 1.0 / (1.0 + (days_ago / 60.0))
            # Quantity bonus: log scale up to 15 points
            qty_bonus = min(math.log1p(total_qty) * 3.0, 15.0)
            base_score = (order_count * 10.0) + qty_bonus
            final_score = base_score * recency_weight
            
            scored_items.append({
                "product": p_display,
                "orderCount": order_count,
                "totalQuantity": round(total_qty, 2) if total_qty % 1 != 0 else int(total_qty),
                "lastPrice": round(last_price, 2),
                "lastOrderedDate": last_date_str,
                "lastOrderedRelative": format_relative_date(last_date_str),
                "recentInvoice": recent_inv,
                "score": round(final_score, 2)
            })
            
        # Sort primarily by calculated score, then by order count, then by last ordered date
        scored_items.sort(key=lambda x: (x["score"], x["orderCount"], x["lastOrderedDate"]), reverse=True)
        recommendations = scored_items[:limit]
        
        return {
            "hasHistory": True,
            "customer": clean_name,
            "recommendations": recommendations,
            "popularProducts": []
        }

def get_popular_products(limit: int = 5):
    """Return top products across all customers for empty-history fallback."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT display_name, latest_price, usage_count, last_used_date
            FROM products
            ORDER BY usage_count DESC, last_used_date DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        
        results = []
        for r in rows:
            results.append({
                "product": r[0],
                "lastPrice": round(r[1], 2),
                "usageCount": r[2],
                "lastOrderedRelative": format_relative_date(r[3])
            })
        return results

def import_historical_data(directories, force_rebuild: bool = False):
    """
    Scan existing invoice folders/files and populate learning database.
    Imports customers, global products, and customer-specific purchase histories.
    """
    init_db()
    
    if force_rebuild:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM customers")
            cursor.execute("DELETE FROM products")
            cursor.execute("DELETE FROM customer_purchases")
            cursor.execute("DELETE FROM processed_invoices")
            conn.commit()
            
    seen_files = set()
    total_customers_imported = 0
    total_purchases_imported = 0
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT invoice_file FROM processed_invoices")
        already_processed = set(r[0] for r in cursor.fetchall())
        
    for d in directories:
        dir_path = Path(d).resolve()
        if not dir_path.exists():
            continue
            
        for f in dir_path.rglob("*.xlsx"):
            if f.name.startswith("~$") or f in seen_files:
                continue
            seen_files.add(f)
            
            if not force_rebuild and f.name in already_processed:
                continue
                
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                wb = openpyxl.load_workbook(str(f), data_only=True)
                ws = wb.active
                
                shop_name = ""
                area = ""
                
                # Check known cells across invoice formats
                for r in range(1, min(15, ws.max_row + 1)):
                    row_vals = [str(ws.cell(r, c).value or "").strip() for c in range(1, 5)]
                    
                    for val in row_vals:
                        if val.startswith("Shop:"):
                            shop_name = val.replace("Shop:", "").strip()
                        elif val.startswith("Shop Name:"):
                            shop_name = val.replace("Shop Name:", "").strip()
                        elif val.startswith("Invoice for "):
                            shop_name = val.replace("Invoice for ", "").strip()
                        elif val.startswith("Area:"):
                            area = val.replace("Area:", "").strip()
                            
                    # Check legacy format where cell A8='Bill To:', A9=Shop, A11=Area
                    if ws.cell(r, 1).value == "Bill To:":
                        s_cand = str(ws.cell(r + 1, 1).value or "").strip()
                        if s_cand and not s_cand.lower().startswith("your company"):
                            shop_name = s_cand
                        a_cand = str(ws.cell(r + 3, 1).value or "").strip()
                        if a_cand:
                            area = a_cand
                            
                # Fallback to parent directory name if under Invoice Storage
                if not shop_name:
                    parent_name = f.parent.name
                    if parent_name and parent_name not in ["Invoice Storage", "web", dir_path.name]:
                        shop_name = parent_name
                        
                if shop_name and shop_name.lower() not in ["your company", "your company name"]:
                    record_customer(shop_name, area, invoice_number=f.stem, date_time=mtime)
                    total_customers_imported += 1
                    
                # Extract products and quantities from rows
                for r in range(1, ws.max_row + 1):
                    col1 = ws.cell(r, 1).value
                    col2 = ws.cell(r, 2).value
                    col3 = ws.cell(r, 3).value
                    col4 = ws.cell(r, 4).value
                    
                    if col1 and isinstance(col1, str):
                        c1_clean = col1.strip()
                        # Skip header labels
                        if c1_clean in ['Product', 'Description', 'Description of Goods', 'Shop:', 'Owner:', 'Area:', 'Contact:', 'BILL TO / BUYER DETAILS:', 'PARTICULARS / GOODS', 'TAX INVOICE', 'SRI LAXMI GAYATRI TRADERS']:
                            continue
                        if 'Total' in c1_clean or 'Invoice' in c1_clean or 'Date' in c1_clean or '═' in c1_clean:
                            continue
                            
                        # Case 1: Qty in col 2, Price in col 3
                        if isinstance(col2, (int, float)) and isinstance(col3, (int, float)) and col3 > 0:
                            qty = float(col2)
                            price = float(col3)
                            record_product(c1_clean, price, invoice_number=f.stem, date_time=mtime)
                            if shop_name:
                                record_customer_purchase(shop_name, c1_clean, quantity=qty, price=price, invoice_number=f.stem, date_time=mtime)
                                total_purchases_imported += 1
                                
                        # Case 2: Sno in col 1, Desc in col 2, Qty in col 3, Price in col 4
                        elif isinstance(col1, int) and col2 and isinstance(col2, str) and isinstance(col4, (int, float)) and col4 > 0:
                            p_name = str(col2).strip()
                            qty = float(col3) if isinstance(col3, (int, float)) else 1.0
                            price = float(col4)
                            record_product(p_name, price, invoice_number=f.stem, date_time=mtime)
                            if shop_name:
                                record_customer_purchase(shop_name, p_name, quantity=qty, price=price, invoice_number=f.stem, date_time=mtime)
                                total_purchases_imported += 1
                                
                # Record in processed_invoices
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT OR IGNORE INTO processed_invoices (invoice_file, customer_norm, processed_at) VALUES (?, ?, ?)",
                        (f.name, normalize_text(shop_name), datetime.now().isoformat())
                    )
                    conn.commit()
                    
            except Exception as err:
                continue
                
    print(f"✅ Learning DB: Processed {len(seen_files)} invoices. Recorded customer-product purchase histories.")
    return {
        "invoices_scanned": len(seen_files),
        "customers_imported": total_customers_imported,
        "purchases_imported": total_purchases_imported
    }

# Initialize DB when module loads
init_db()
