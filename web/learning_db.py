import sqlite3
import os
import re
import math
from pathlib import Path
from datetime import datetime, timedelta
import openpyxl
import tempfile
import shutil

DB_PATH = Path(__file__).resolve().parent / "invoice_learning.db"

def get_connection():
    """Get SQLite database connection with row factory."""
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
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
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                created_at TIMESTAMP NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL,
                customer_norm TEXT NOT NULL,
                product_norm TEXT NOT NULL,
                product_display TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                total_amount REAL NOT NULL,
                item_order INTEGER DEFAULT 1
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_invoices (
                invoice_file TEXT UNIQUE NOT NULL,
                customer_norm TEXT NOT NULL,
                processed_at TIMESTAMP NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoice_edit_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL,
                edited_at TIMESTAMP NOT NULL,
                old_customer TEXT,
                new_customer TEXT,
                old_total REAL,
                new_total REAL,
                changes_summary TEXT
            )
        """)
        try:
            cursor.execute("ALTER TABLE invoices ADD COLUMN updated_at TIMESTAMP")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE invoices ADD COLUMN extra_charges_desc TEXT")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE invoices ADD COLUMN extra_charges_amount REAL DEFAULT 0.0")
        except Exception:
            pass
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_norm ON customers(normalized_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_rank ON customers(usage_count DESC, last_used_date DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_norm ON products(normalized_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_rank ON products(usage_count DESC, last_used_date DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cp_cust ON customer_purchases(customer_norm)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cp_order_count ON customer_purchases(customer_norm, order_count DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inv_num ON invoices(invoice_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inv_cust ON invoices(customer_norm)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inv_date ON invoices(invoice_date DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inv_amt ON invoices(total_amount DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_inv ON invoice_items(invoice_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_prod ON invoice_items(product_norm)")
        conn.commit()

def record_customer(shop_name: str, area: str = "", invoice_number: str = "", date_time: datetime = None):
    """Record or update customer usage."""
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
    """Record or update global product usage."""
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
    """Record or update customer-specific product purchase history."""
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

def record_invoice(
    invoice_number: str,
    customer_name: str,
    area: str,
    products: list,
    invoice_type: str = 'current',
    invoice_date: datetime = None,
    total_amount: float = None,
    file_path: str = '',
    filename: str = '',
    extra_charges_desc: str = '',
    extra_charges_amount: float = 0.0
):
    """
    Persist full invoice metadata and line items to SQLite database.
    Also updates customer records, product records, and customer_purchases.
    """
    if not invoice_number:
        return
    c_norm = normalize_text(customer_name)
    c_display = " ".join(str(customer_name or "").strip().split())
    clean_area = " ".join(str(area or "").strip().split())
    clean_extra_desc = str(extra_charges_desc or '').strip()
    try:
        clean_extra_amt = float(extra_charges_amount or 0.0)
    except (ValueError, TypeError):
        clean_extra_amt = 0.0
    if clean_extra_amt < 0:
        clean_extra_amt = 0.0
    
    if not invoice_date:
        invoice_date = datetime.now()
    date_iso = invoice_date.isoformat()
    
    calc_total = 0.0
    calc_qty = 0.0
    items_to_save = []
    
    for idx, p in enumerate(products):
        p_name = " ".join(str(p.get('name') or p.get('productName') or '').strip().split())
        p_norm = normalize_text(p_name)
        if not p_name:
            continue
        try:
            qty = float(p.get('quantity', 1.0))
        except (ValueError, TypeError):
            qty = 1.0
        try:
            price_val = p.get('price') if p.get('price') is not None else p.get('unitPrice')
            price = float(price_val if price_val is not None else 0.0)
        except (ValueError, TypeError):
            price = 0.0
        line_tot = qty * price
        calc_total += line_tot
        calc_qty += qty
        items_to_save.append((p_norm, p_name, qty, price, line_tot, idx + 1))
        
    if total_amount is not None:
        final_amount = float(total_amount)
    else:
        final_amount = calc_total + clean_extra_amt
    
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO invoices (
                invoice_number, customer_norm, customer_display, area,
                invoice_date, invoice_type, product_count, total_quantity,
                total_amount, file_path, filename, created_at,
                extra_charges_desc, extra_charges_amount
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(invoice_number) DO UPDATE SET
                customer_norm = excluded.customer_norm,
                customer_display = excluded.customer_display,
                area = excluded.area,
                invoice_date = excluded.invoice_date,
                invoice_type = excluded.invoice_type,
                product_count = excluded.product_count,
                total_quantity = excluded.total_quantity,
                total_amount = excluded.total_amount,
                file_path = excluded.file_path,
                filename = excluded.filename,
                extra_charges_desc = excluded.extra_charges_desc,
                extra_charges_amount = excluded.extra_charges_amount
        """, (
            invoice_number, c_norm, c_display, clean_area,
            date_iso, invoice_type, len(items_to_save), calc_qty,
            final_amount, str(file_path or ''), str(filename or ''),
            datetime.now().isoformat(),
            clean_extra_desc, clean_extra_amt
        ))
        
        cursor.execute("DELETE FROM invoice_items WHERE invoice_number = ?", (invoice_number,))
        for p_norm, p_name, qty, price, line_tot, order_idx in items_to_save:
            cursor.execute("""
                INSERT INTO invoice_items (
                    invoice_number, customer_norm, product_norm, product_display,
                    quantity, price, total_amount, item_order
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (invoice_number, c_norm, p_norm, p_name, qty, price, line_tot, order_idx))
            
        conn.commit()
        
    record_customer(customer_name, area=clean_area, invoice_number=invoice_number, date_time=invoice_date)
    for p_norm, p_name, qty, price, line_tot, _ in items_to_save:
        record_product(p_name, price=price, invoice_number=invoice_number, date_time=invoice_date)
        record_customer_purchase(customer_name, p_name, quantity=qty, price=price, invoice_number=invoice_number, date_time=invoice_date)

def search_customers(query: str, limit: int = 10):
    """Search customer suggestions by prefix / substring."""
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
    """Search product suggestions by prefix / substring."""
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

def format_date_display(dt_str: str) -> str:
    """Helper to format ISO timestamp as DD MMM YYYY."""
    try:
        dt = datetime.fromisoformat(str(dt_str).replace("Z", ""))
        return dt.strftime('%d %b %Y')
    except Exception:
        return str(dt_str or "")[:10]

def get_customer_recommendations(shop_name: str, limit: int = 8):
    """Returns recommendations based on customer's order history."""
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
                
            recency_weight = 1.0 / (1.0 + (days_ago / 60.0))
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

def get_date_cutoff(date_range: str):
    """Returns ISO datetime string cutoff for a given date range string."""
    now = datetime.now()
    if date_range == '7d':
        return (now - timedelta(days=7)).isoformat()
    elif date_range == '30d':
        return (now - timedelta(days=30)).isoformat()
    elif date_range == 'this_year':
        return datetime(now.year, 1, 1).isoformat()
    return None

def get_dashboard_analytics(date_range: str = 'all'):
    """
    Calculates summary metrics, periodic sales trend, and recent invoices.
    Strictly uses real saved invoice data from SQLite database.
    """
    init_db()
    cutoff = get_date_cutoff(date_range)
    now = datetime.now()
    month_start = datetime(now.year, now.month, 1).isoformat()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Total Invoices, Total Sales, Avg Order Value within range
        if cutoff:
            cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(total_amount), 0), COALESCE(AVG(total_amount), 0)
                FROM invoices
                WHERE invoice_date >= ?
            """, (cutoff,))
        else:
            cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(total_amount), 0), COALESCE(AVG(total_amount), 0)
                FROM invoices
            """)
        tot_inv, tot_sales, avg_order = cursor.fetchone()
        
        # 2. This Month's Sales
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0)
            FROM invoices
            WHERE invoice_date >= ?
        """, (month_start,))
        this_month_sales = cursor.fetchone()[0]
        
        # 3. Total Customers and Total Products count
        cursor.execute("SELECT COUNT(*) FROM customers")
        total_customers = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM products")
        total_products = cursor.fetchone()[0]
        
        # 4. Recent Invoices (top 7)
        cursor.execute("""
            SELECT invoice_number, customer_display, area, invoice_date, invoice_type, product_count, total_amount, filename
            FROM invoices
            ORDER BY invoice_date DESC
            LIMIT 7
        """)
        recent_rows = cursor.fetchall()
        recent_invoices = []
        for r in recent_rows:
            recent_invoices.append({
                "invoiceNumber": r[0],
                "customerName": r[1],
                "area": r[2],
                "date": r[3],
                "dateFormatted": format_date_display(r[3]),
                "relativeDate": format_relative_date(r[3]),
                "invoiceType": r[4],
                "productCount": r[5],
                "totalAmount": round(r[6], 2),
                "filename": r[7],
                "downloadUrl": f"/api/download/{r[7]}" if r[7] else ""
            })
            
        # 5. Sales Chart Data
        # If range is 7d or 30d, group by day; else group by month
        chart_labels = []
        chart_values = []
        chart_orders = []
        
        if date_range in ['7d', '30d']:
            cursor.execute("""
                SELECT strftime('%Y-%m-%d', invoice_date) as day, SUM(total_amount), COUNT(*)
                FROM invoices
                WHERE invoice_date >= ?
                GROUP BY day
                ORDER BY day ASC
            """, (cutoff,))
            chart_rows = cursor.fetchall()
            for day_str, amt, cnt in chart_rows:
                try:
                    d_dt = datetime.strptime(day_str, '%Y-%m-%d')
                    lbl = d_dt.strftime('%d %b')
                except Exception:
                    lbl = day_str
                chart_labels.append(lbl)
                chart_values.append(round(amt, 2))
                chart_orders.append(cnt)
        else:
            # Group by year-month
            where_clause = f"WHERE invoice_date >= '{cutoff}'" if cutoff else ""
            cursor.execute(f"""
                SELECT strftime('%Y-%m', invoice_date) as ym, SUM(total_amount), COUNT(*)
                FROM invoices
                {where_clause}
                GROUP BY ym
                ORDER BY ym ASC
            """)
            chart_rows = cursor.fetchall()
            for ym_str, amt, cnt in chart_rows:
                try:
                    d_dt = datetime.strptime(ym_str, '%Y-%m')
                    lbl = d_dt.strftime('%b %Y')
                except Exception:
                    lbl = ym_str
                chart_labels.append(lbl)
                chart_values.append(round(amt, 2))
                chart_orders.append(cnt)
                
        return {
            "dateRange": date_range,
            "metrics": {
                "totalInvoices": tot_inv,
                "totalSales": round(tot_sales, 2),
                "totalRevenue": round(tot_sales, 2),
                "thisMonthSales": round(this_month_sales, 2),
                "averageOrderValue": round(avg_order, 2),
                "totalCustomers": total_customers,
                "totalProducts": total_products
            },
            "recentInvoices": recent_invoices,
            "chart": {
                "labels": chart_labels,
                "sales": chart_values,
                "orders": chart_orders
            }
        }

def get_all_invoices(
    q: str = '',
    customer: str = '',
    date_range: str = 'all',
    type_filter: str = '',
    sort_by: str = 'date',
    sort_order: str = 'desc',
    limit: int = 100
):
    """
    Searchable, filterable, sortable list of all saved invoices.
    """
    init_db()
    conditions = []
    params = []
    
    if q:
        norm_q = f"%{normalize_text(q)}%"
        conditions.append("""(
            customer_norm LIKE ? OR invoice_number LIKE ? OR customer_display LIKE ? OR area LIKE ?
            OR invoice_number IN (SELECT invoice_number FROM invoice_items WHERE product_norm LIKE ?)
        )""")
        params.extend([norm_q, f"%{q.strip()}%", f"%{q.strip()}%", f"%{q.strip()}%", norm_q])
        
    if customer:
        c_norm = normalize_text(customer)
        conditions.append("customer_norm = ?")
        params.append(c_norm)
        
    cutoff = get_date_cutoff(date_range)
    if cutoff:
        conditions.append("invoice_date >= ?")
        params.append(cutoff)
        
    if type_filter and type_filter in ['current', 'all']:
        conditions.append("invoice_type = ?")
        params.append(type_filter)
        
    where_sql = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    
    sort_col_map = {
        'date': 'invoice_date',
        'amount': 'total_amount',
        'customer': 'customer_display',
        'number': 'invoice_number'
    }
    col = sort_col_map.get(sort_by, 'invoice_date')
    order = "ASC" if sort_order.lower() == 'asc' else "DESC"
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Total counts & sums
        cursor.execute(f"SELECT COUNT(*), COALESCE(SUM(total_amount), 0) FROM invoices {where_sql}", params)
        total_count, total_sum = cursor.fetchone()
        
        # Fetch rows
        query_sql = f"""
            SELECT invoice_number, customer_display, area, invoice_date, invoice_type, product_count, total_amount, filename, file_path
            FROM invoices
            {where_sql}
            ORDER BY {col} {order}
            LIMIT ?
        """
        cursor.execute(query_sql, params + [limit])
        rows = cursor.fetchall()
        
        # Distinct customers for filter dropdown
        cursor.execute("SELECT DISTINCT customer_display FROM invoices ORDER BY customer_display ASC")
        customer_options = [r[0] for r in cursor.fetchall() if r[0]]
        
        invoices = []
        for r in rows:
            invoices.append({
                "invoiceNumber": r[0],
                "customerName": r[1],
                "area": r[2],
                "date": r[3],
                "dateFormatted": format_date_display(r[3]),
                "relativeDate": format_relative_date(r[3]),
                "invoiceType": r[4],
                "productCount": r[5],
                "totalAmount": round(r[6], 2),
                "filename": r[7],
                "downloadUrl": f"/api/download/{r[7]}" if r[7] else ""
            })
            
        return {
            "invoices": invoices,
            "totalCount": total_count,
            "totalAmount": round(total_sum, 2),
            "customerOptions": customer_options
        }

def get_invoice_detail(invoice_number: str):
    """Get full details of a specific invoice including customer, line items, and files."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT invoice_number, customer_display, area, invoice_date, invoice_type, product_count, total_quantity, total_amount, filename, file_path, extra_charges_desc, extra_charges_amount
            FROM invoices
            WHERE invoice_number = ?
        """, (invoice_number,))
        row = cursor.fetchone()
        if not row:
            return None
            
        cursor.execute("""
            SELECT product_display, quantity, price, total_amount, item_order
            FROM invoice_items
            WHERE invoice_number = ?
            ORDER BY item_order ASC
        """, (invoice_number,))
        item_rows = cursor.fetchall()
        
        products = []
        for it in item_rows:
            products.append({
                "name": it[0],
                "productName": it[0],
                "quantity": it[1],
                "price": it[2],
                "total": it[3]
            })
            
        subtotal = round(sum(p["total"] for p in products), 2)
        extra_desc = row[10] if (len(row) > 10 and row[10]) else ""
        extra_amt = float(row[11]) if (len(row) > 11 and row[11] is not None) else 0.0

        return {
            "invoiceNumber": row[0],
            "customerName": row[1],
            "area": row[2],
            "date": row[3],
            "dateFormatted": format_date_display(row[3]),
            "invoiceType": row[4],
            "productCount": row[5],
            "totalQuantity": row[6],
            "productSubtotal": subtotal,
            "extraChargesDesc": extra_desc,
            "extraChargesAmount": round(extra_amt, 2),
            "totalAmount": round(row[7], 2),
            "filename": row[8],
            "downloadUrl": f"/api/download/{row[8]}" if row[8] else "",
            "products": products,
            "items": products
        }

def get_customers_overview(q: str = '', sort_by: str = 'amount'):
    """
    Overview of all customers: invoice counts, total spend, last invoice date, top products.
    """
    init_db()
    where_clause = ""
    params = []
    if q:
        norm_q = f"%{normalize_text(q)}%"
        where_clause = "WHERE c.normalized_name LIKE ? OR c.area LIKE ?"
        params = [norm_q, f"%{q.strip()}%"]
        
    sort_map = {
        'amount': 'total_amount DESC',
        'invoices': 'invoice_count DESC',
        'name': 'c.display_name ASC',
        'last_date': 'last_date DESC'
    }
    order_by_sql = sort_map.get(sort_by, 'total_amount DESC')
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT 
                c.display_name,
                c.area,
                COUNT(i.id) as invoice_count,
                COALESCE(SUM(i.total_amount), 0) as total_amount,
                COALESCE(MAX(i.invoice_date), c.last_used_date) as last_date,
                c.normalized_name
            FROM customers c
            LEFT JOIN invoices i ON c.normalized_name = i.customer_norm
            {where_clause}
            GROUP BY c.normalized_name
            ORDER BY {order_by_sql}
        """, params)
        rows = cursor.fetchall()
        
        customers = []
        for r in rows:
            c_disp, area, inv_count, tot_amt, last_dt, c_norm = r
            
            # Fetch top 2 purchased products for this customer
            cursor.execute("""
                SELECT product_display, order_count, last_price
                FROM customer_purchases
                WHERE customer_norm = ?
                ORDER BY order_count DESC, last_ordered_date DESC
                LIMIT 2
            """, (c_norm,))
            top_prods = cursor.fetchall()
            top_products_list = [{"name": tp[0], "orders": tp[1], "lastPrice": tp[2]} for tp in top_prods]
            
            customers.append({
                "customerName": c_disp,
                "area": area,
                "invoiceCount": inv_count,
                "totalAmount": round(tot_amt, 2),
                "lastDate": last_dt,
                "lastDateFormatted": format_date_display(last_dt),
                "relativeDate": format_relative_date(last_dt),
                "topProducts": top_products_list
            })
            
        return customers

def get_customer_profile(customer_name: str):
    """Detailed profile of a customer: full invoices list, total spend, recommendations."""
    init_db()
    c_norm = normalize_text(customer_name)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT display_name, area, usage_count, last_used_date
            FROM customers
            WHERE normalized_name = ?
        """, (c_norm,))
        row = cursor.fetchone()
        if not row:
            return None
            
        c_disp, area, usage_cnt, last_used = row
        
        # Invoices for this customer
        cursor.execute("""
            SELECT invoice_number, invoice_date, invoice_type, product_count, total_amount, filename
            FROM invoices
            WHERE customer_norm = ?
            ORDER BY invoice_date DESC
        """, (c_norm,))
        inv_rows = cursor.fetchall()
        
        invoices = []
        total_spend = 0.0
        for ir in inv_rows:
            total_spend += ir[4]
            invoices.append({
                "invoiceNumber": ir[0],
                "date": ir[1],
                "dateFormatted": format_date_display(ir[1]),
                "invoiceType": ir[2],
                "productCount": ir[3],
                "totalAmount": round(ir[4], 2),
                "filename": ir[5],
                "downloadUrl": f"/api/download/{ir[5]}" if ir[5] else ""
            })
            
        # Recommendations
        rec_data = get_customer_recommendations(customer_name, limit=8)
        
        return {
            "customerName": c_disp,
            "area": area,
            "invoiceCount": len(invoices),
            "totalSpend": round(total_spend, 2),
            "averageOrderValue": round(total_spend / len(invoices), 2) if invoices else 0.0,
            "lastDateFormatted": format_date_display(last_used),
            "invoices": invoices,
            "frequentlyOrdered": rec_data.get("recommendations", [])
        }

def get_products_overview(q: str = '', sort_by: str = 'quantity'):
    """
    Overview of all products: last price, average price, total quantity sold, invoice occurrences, buyers count.
    """
    init_db()
    where_clause = ""
    params = []
    if q:
        norm_q = f"%{normalize_text(q)}%"
        where_clause = "WHERE p.normalized_name LIKE ?"
        params = [norm_q]
        
    sort_map = {
        'quantity': 'total_qty DESC',
        'invoices': 'invoice_count DESC',
        'sales': 'total_sales DESC',
        'name': 'p.display_name ASC',
        'price': 'p.latest_price DESC'
    }
    order_by_sql = sort_map.get(sort_by, 'total_qty DESC')
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT 
                p.display_name,
                p.latest_price,
                COALESCE(SUM(it.quantity), 0) as total_qty,
                COALESCE(SUM(it.total_amount), 0) as total_sales,
                COALESCE(AVG(it.price), p.latest_price) as avg_price,
                COUNT(DISTINCT it.invoice_number) as invoice_count,
                COUNT(DISTINCT it.customer_norm) as customer_count,
                COALESCE(MAX(i.invoice_date), p.last_used_date) as last_sold,
                p.normalized_name
            FROM products p
            LEFT JOIN invoice_items it ON p.normalized_name = it.product_norm
            LEFT JOIN invoices i ON it.invoice_number = i.invoice_number
            {where_clause}
            GROUP BY p.normalized_name
            ORDER BY {order_by_sql}
        """, params)
        rows = cursor.fetchall()
        
        products = []
        for r in rows:
            p_disp, last_price, tot_qty, tot_sales, avg_price, inv_cnt, cust_cnt, last_sold, p_norm = r
            products.append({
                "productName": p_disp,
                "lastPrice": round(last_price, 2),
                "avgPrice": round(avg_price, 2),
                "totalQuantitySold": round(tot_qty, 2) if tot_qty % 1 != 0 else int(tot_qty),
                "totalSales": round(tot_sales, 2),
                "invoiceCount": inv_cnt,
                "customerCount": cust_cnt,
                "lastSoldDate": last_sold,
                "lastSoldFormatted": format_date_display(last_sold),
                "relativeDate": format_relative_date(last_sold)
            })
            
        return products

def get_product_profile(product_name: str):
    """Detailed profile of a product: price history, buyers, invoices list."""
    init_db()
    p_norm = normalize_text(product_name)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT display_name, latest_price, usage_count, last_used_date
            FROM products
            WHERE normalized_name = ?
        """, (p_norm,))
        row = cursor.fetchone()
        if not row:
            return None
            
        p_disp, latest_price, usage_cnt, last_used = row
        
        # Customers who bought this product
        cursor.execute("""
            SELECT customer_display, order_count, total_quantity, last_price, last_ordered_date
            FROM customer_purchases
            WHERE product_norm = ?
            ORDER BY order_count DESC, total_quantity DESC
        """, (p_norm,))
        cust_rows = cursor.fetchall()
        
        customers = []
        tot_qty = 0.0
        tot_revenue = 0.0
        for cr in cust_rows:
            tot_qty += cr[2]
            tot_revenue += (cr[2] * cr[3])
            customers.append({
                "customerName": cr[0],
                "orderCount": cr[1],
                "totalQuantity": round(cr[2], 2) if cr[2] % 1 != 0 else int(cr[2]),
                "lastPrice": round(cr[3], 2),
                "lastOrderedDate": format_date_display(cr[4])
            })
            
        # Recent invoices containing this product
        cursor.execute("""
            SELECT i.invoice_number, i.customer_display, it.quantity, it.price, it.total_amount, i.invoice_date, i.filename
            FROM invoice_items it
            JOIN invoices i ON it.invoice_number = i.invoice_number
            WHERE it.product_norm = ?
            ORDER BY i.invoice_date DESC
            LIMIT 15
        """, (p_norm,))
        inv_rows = cursor.fetchall()
        
        invoices = []
        for ir in inv_rows:
            invoices.append({
                "invoiceNumber": ir[0],
                "customerName": ir[1],
                "quantity": ir[2],
                "price": ir[3],
                "total": ir[4],
                "dateFormatted": format_date_display(ir[5]),
                "filename": ir[6],
                "downloadUrl": f"/api/download/{ir[6]}" if ir[6] else ""
            })
            
        return {
            "productName": p_disp,
            "latestPrice": round(latest_price, 2),
            "totalQuantitySold": round(tot_qty, 2) if tot_qty % 1 != 0 else int(tot_qty),
            "totalRevenue": round(tot_revenue, 2),
            "customerCount": len(customers),
            "invoiceCount": len(invoices),
            "customers": customers,
            "recentInvoices": invoices
        }

def import_historical_data(directories, force_rebuild: bool = False):
    """
    Scan existing invoice folders/files and populate learning database.
    Imports customers, global products, customer purchases, and full invoice records.
    """
    init_db()
    
    if force_rebuild:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM customers")
            cursor.execute("DELETE FROM products")
            cursor.execute("DELETE FROM customer_purchases")
            cursor.execute("DELETE FROM invoices")
            cursor.execute("DELETE FROM invoice_items")
            cursor.execute("DELETE FROM processed_invoices")
            conn.commit()
            
    seen_files = set()
    total_invoices_imported = 0
    
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
                inv_num = ""
                inv_date = None
                total_val = None
                products = []
                
                # Check header metadata
                for r in range(1, min(20, ws.max_row + 1)):
                    for c in range(1, 6):
                        val = str(ws.cell(r, c).value or "").strip()
                        if "Shop:" in val:
                            shop_name = val.replace("Shop:", "").strip()
                        elif "Shop Name:" in val:
                            shop_name = val.replace("Shop Name:", "").strip()
                        elif "Invoice for " in val:
                            shop_name = val.replace("Invoice for ", "").strip()
                        elif "Area:" in val:
                            area = val.replace("Area:", "").strip()
                        elif "Invoice No:" in val or "Invoice Number:" in val:
                            inv_num = val.replace("Invoice No:", "").replace("Invoice Number:", "").strip()
                        elif "Date:" in val and not inv_date:
                            d_str = val.replace("Date:", "").replace("📅", "").strip()
                            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d %b %Y']:
                                try:
                                    inv_date = datetime.strptime(d_str, fmt)
                                    break
                                except Exception:
                                    pass
                                    
                    if ws.cell(r, 1).value == "Bill To:":
                        s_cand = str(ws.cell(r + 1, 1).value or "").strip()
                        if s_cand and not s_cand.lower().startswith("your company"):
                            shop_name = s_cand
                        a_cand = str(ws.cell(r + 3, 1).value or "").strip()
                        if a_cand:
                            area = a_cand
                            
                if not shop_name:
                    parent_name = f.parent.name
                    if parent_name and parent_name not in ["Invoice Storage", "web", dir_path.name]:
                        shop_name = parent_name
                        
                if not shop_name or shop_name.lower() in ["your company", "your company name"]:
                    shop_name = "Wholesale Customer"
                    
                if not inv_num:
                    inv_num = f.stem
                    
                if not inv_date:
                    inv_date = mtime
                    
                # Extract products and total
                for r in range(1, ws.max_row + 1):
                    c1 = ws.cell(r, 1).value
                    c2 = ws.cell(r, 2).value
                    c3 = ws.cell(r, 3).value
                    c4 = ws.cell(r, 4).value
                    c5 = ws.cell(r, 5).value
                    
                    row_str = ' '.join(str(ws.cell(r, c).value or '') for c in range(1, 6)).upper()
                    if 'GRAND TOTAL' in row_str or 'TOTAL AMOUNT' in row_str or 'TOTAL' in row_str:
                        for val in [c5, c4, c3, c2]:
                            if isinstance(val, (int, float)) and val > 0:
                                if total_val is None or 'GRAND' in row_str:
                                    total_val = float(val)
                                    break
                                    
                    if c1 and isinstance(c1, str):
                        c1_s = c1.strip()
                        if c1_s in ['Product', 'Description', 'Description of Goods', 'Shop:', 'Owner:', 'Area:', 'Contact:', 'BILL TO / BUYER DETAILS:', 'PARTICULARS / GOODS', 'TAX INVOICE', 'SRI LAXMI GAYATRI TRADERS']:
                            continue
                        if 'Total' in c1_s or 'Invoice' in c1_s or 'Date' in c1_s or '═' in c1_s:
                            continue
                        if isinstance(c2, (int, float)) and isinstance(c3, (int, float)) and c3 > 0:
                            products.append({'name': c1_s, 'quantity': float(c2), 'price': float(c3)})
                        elif isinstance(c1, int) and c2 and isinstance(c2, str) and isinstance(c4, (int, float)) and c4 > 0:
                            qty = float(c3) if isinstance(c3, (int, float)) else 1.0
                            products.append({'name': str(c2).strip(), 'quantity': qty, 'price': float(c4)})
                            
                calc_tot = sum(p['quantity'] * p['price'] for p in products)
                if total_val is None or total_val <= 0:
                    total_val = calc_tot
                    
                # Record full invoice
                record_invoice(
                    invoice_number=inv_num,
                    customer_name=shop_name,
                    area=area,
                    products=products,
                    invoice_type='current',
                    invoice_date=inv_date,
                    total_amount=total_val,
                    file_path=str(f),
                    filename=f.name
                )
                total_invoices_imported += 1
                
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT OR IGNORE INTO processed_invoices (invoice_file, customer_norm, processed_at) VALUES (?, ?, ?)",
                        (f.name, normalize_text(shop_name), datetime.now().isoformat())
                    )
                    conn.commit()
                    
            except Exception as err:
                continue
                
    print(f"✅ Learning DB: Successfully indexed {total_invoices_imported} invoices.")
    return {
        "invoices_scanned": len(seen_files),
        "invoices_imported": total_invoices_imported
    }

def reset_all_learning_data():
    """
    Permanently delete all business data from the SQLite database:
    - invoice_items
    - invoices
    - customer_purchases
    - customers
    - products
    - processed_invoices
    Resets schema and vacuums database file.
    """
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM invoice_items")
        cursor.execute("DELETE FROM invoices")
        cursor.execute("DELETE FROM customer_purchases")
        cursor.execute("DELETE FROM customers")
        cursor.execute("DELETE FROM products")
        cursor.execute("DELETE FROM processed_invoices")
        conn.commit()
        cursor.execute("VACUUM")
    print("🧹 SQLite database tables wiped and vacuumed.")

def get_reset_preview(storage_dir=None):
    """
    Get counts of invoices, customers, products, and storage folders to be deleted.
    """
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM invoices")
        inv_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM customers")
        cust_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM products")
        prod_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM invoice_items")
        items_count = cursor.fetchone()[0]
        
    folders_count = 0
    files_count = 0
    if storage_dir and Path(storage_dir).exists():
        s_path = Path(storage_dir)
        for item in s_path.iterdir():
            if item.is_dir():
                folders_count += 1
                for f in item.glob('*.xlsx'):
                    if f.is_file():
                        files_count += 1
            elif item.is_file() and item.suffix.lower() == '.xlsx':
                files_count += 1
                
    return {
        "invoicesCount": max(inv_count, files_count),
        "customersCount": cust_count,
        "productsCount": prod_count,
        "itemsCount": items_count,
        "foldersCount": folders_count
    }

def delete_invoice_by_number(invoice_number: str, storage_dir=None):
    """
    Safely delete a single invoice:
    - Removes invoice spreadsheet file from customer folder.
    - Removes records from invoice_items and invoices.
    - Recalculates customer_purchases for affected customer and products.
    - Updates usage_count for customer and products.
    - Preserves customer and product catalog records even if usage reaches 0.
    """
    init_db()
    if not invoice_number:
        return None
        
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, customer_norm, customer_display, file_path, filename, total_amount, invoice_date
            FROM invoices
            WHERE invoice_number = ?
        """, (invoice_number,))
        row = cursor.fetchone()
        if not row:
            return None
            
        inv_id, c_norm, c_disp, f_path, f_name, tot_amt, inv_date = row
        
        # Get all products in this invoice
        cursor.execute("""
            SELECT product_norm, product_display, quantity, price
            FROM invoice_items
            WHERE invoice_number = ?
        """, (invoice_number,))
        item_rows = cursor.fetchall()
        affected_prods = list(set([r[0] for r in item_rows]))
        
        # 1. Delete rows from database
        cursor.execute("DELETE FROM invoice_items WHERE invoice_number = ?", (invoice_number,))
        cursor.execute("DELETE FROM invoices WHERE invoice_number = ?", (invoice_number,))
        cursor.execute("DELETE FROM processed_invoices WHERE invoice_file = ? OR invoice_file = ?", (f_name, f_path))
        
        # 2. Recalculate customer_purchases for affected products and customer
        for p_norm in affected_prods:
            cursor.execute("""
                SELECT COUNT(DISTINCT ii.invoice_number), COALESCE(SUM(ii.quantity), 0), 
                       COALESCE(MAX(ii.price), 0), COALESCE(MAX(i.invoice_date), '')
                FROM invoice_items ii
                JOIN invoices i ON ii.invoice_number = i.invoice_number
                WHERE ii.customer_norm = ? AND ii.product_norm = ?
            """, (c_norm, p_norm))
            agg = cursor.fetchone()
            rem_count, rem_qty, last_pr, last_dt = agg
            if rem_count > 0:
                cursor.execute("""
                    UPDATE customer_purchases
                    SET order_count = ?, total_quantity = ?, last_price = ?, last_ordered_date = ?
                    WHERE customer_norm = ? AND product_norm = ?
                """, (rem_count, rem_qty, last_pr, last_dt, c_norm, p_norm))
            else:
                cursor.execute("DELETE FROM customer_purchases WHERE customer_norm = ? AND product_norm = ?", (c_norm, p_norm))
                
        # 3. Update customer usage count and last date (keep customer record in catalog)
        cursor.execute("""
            SELECT COUNT(*), COALESCE(MAX(invoice_date), '')
            FROM invoices
            WHERE customer_norm = ?
        """, (c_norm,))
        cust_agg = cursor.fetchone()
        rem_invs, cust_last_dt = cust_agg
        cursor.execute("""
            UPDATE customers
            SET usage_count = ?, last_used_date = CASE WHEN ? != '' THEN ? ELSE last_used_date END
            WHERE normalized_name = ?
        """, (rem_invs, cust_last_dt, cust_last_dt, c_norm))
        
        # 4. Update products usage count (keep product in catalog)
        for p_norm in affected_prods:
            cursor.execute("""
                SELECT COUNT(DISTINCT ii.invoice_number), COALESCE(MAX(i.invoice_date), '')
                FROM invoice_items ii
                JOIN invoices i ON ii.invoice_number = i.invoice_number
                WHERE ii.product_norm = ?
            """, (p_norm,))
            prod_agg = cursor.fetchone()
            p_count, p_last_dt = prod_agg
            cursor.execute("""
                UPDATE products
                SET usage_count = ?, last_used_date = CASE WHEN ? != '' THEN ? ELSE last_used_date END
                WHERE normalized_name = ?
            """, (p_count, p_last_dt, p_last_dt, p_norm))
            
        conn.commit()
        
    # 5. Safely delete file from disk inside storage_dir (Excel, PDF, and related references)
    file_deleted = False
    if storage_dir:
        storage_path = Path(storage_dir).resolve()
        import gc, time
        gc.collect()

        # Gather base stems for this invoice
        base_stems = set()
        if f_name:
            base_stems.add(Path(f_name).stem)
        if invoice_number:
            base_stems.add(invoice_number)

        # Check by direct f_path
        if f_path:
            fp = Path(f_path).resolve()
            if fp.exists() and fp.is_file() and fp.is_relative_to(storage_path):
                for attempt in range(4):
                    try:
                        fp.unlink()
                        file_deleted = True
                        break
                    except Exception as e:
                        if attempt < 3:
                            time.sleep(0.08)
                            gc.collect()
                        else:
                            print(f"Warning deleting file {fp}: {e}")

        # Check for related files (.xlsx, .xls, .pdf) in storage_dir (customer folders, product folders)
        for stem in base_stems:
            if not stem:
                continue
            for ext in ['.xlsx', '.xls', '.pdf']:
                target_fname = f"{stem}{ext}"
                for p in storage_path.rglob(target_fname):
                    if p.is_file() and p.resolve().is_relative_to(storage_path):
                        for attempt in range(4):
                            try:
                                p.unlink()
                                file_deleted = True
                                break
                            except Exception as e:
                                if attempt < 3:
                                    time.sleep(0.08)
                                    gc.collect()
                                else:
                                    print(f"Warning deleting related file {p}: {e}")

        # Also clean from tempdir
        for stem in base_stems:
            for ext in ['.xlsx', '.xls', '.pdf']:
                temp_file = Path(tempfile.gettempdir()) / f"{stem}{ext}"
                if temp_file.exists() and temp_file.is_file():
                    try:
                        temp_file.unlink()
                    except Exception:
                        pass
                
    return {
        "invoiceNumber": invoice_number,
        "customerName": c_disp,
        "totalAmount": tot_amt,
        "fileDeleted": file_deleted
    }

def bulk_delete_invoices(invoice_numbers: list, storage_dir=None):
    """Delete multiple selected invoices safely."""
    if not invoice_numbers or not isinstance(invoice_numbers, list):
        return {"deletedCount": 0, "failedCount": 0, "totalAmount": 0.0, "deletedInvoices": [], "failedInvoices": []}
        
    deleted = []
    failed = []
    total_amt = 0.0
    for inv_num in invoice_numbers:
        clean_num = str(inv_num).strip()
        if not clean_num:
            continue
        res = delete_invoice_by_number(clean_num, storage_dir=storage_dir)
        if res:
            deleted.append(res["invoiceNumber"])
            total_amt += res["totalAmount"]
        else:
            failed.append(clean_num)
            
    return {
        "deletedCount": len(deleted),
        "failedCount": len(failed),
        "totalAmount": round(total_amt, 2),
        "deletedInvoices": deleted,
        "failedInvoices": failed
    }

def update_invoice_record(
    invoice_number: str,
    customer: dict,
    products: list,
    invoice_type: str = 'current',
    new_file_path: str = '',
    new_filename: str = '',
    storage_dir = None,
    extra_charges_desc: str = None,
    extra_charges_amount: float = None
):
    """
    Safely update an existing invoice:
    - Retains original invoice number.
    - Updates invoices table (customer, area, invoice_type, totals, file_path, filename, extra charges, updated_at).
    - Replaces line items in invoice_items table.
    - Ensures customer and products exist in catalog.
    - Recalculates customer usage counts, product usage counts, and customer_purchases pairs.
    - Records edit in invoice_edit_history.
    - Returns updated invoice record dictionary.
    """
    init_db()
    if not invoice_number:
        return None

    clean_inv_num = str(invoice_number).strip()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, customer_norm, customer_display, area, invoice_date, invoice_type, total_amount, file_path, filename, extra_charges_desc, extra_charges_amount
            FROM invoices
            WHERE invoice_number = ?
        """, (clean_inv_num,))
        old_row = cursor.fetchone()
        if not old_row:
            return None

        old_id, old_c_norm, old_c_disp, old_area, inv_date, old_type, old_tot, old_fpath, old_fname = old_row[:9]
        old_extra_desc = old_row[9] if (len(old_row) > 9 and old_row[9]) else ""
        old_extra_amt = float(old_row[10]) if (len(old_row) > 10 and old_row[10] is not None) else 0.0

        clean_extra_desc = str(extra_charges_desc if extra_charges_desc is not None else old_extra_desc).strip()
        try:
            clean_extra_amt = float(extra_charges_amount if extra_charges_amount is not None else old_extra_amt)
        except (ValueError, TypeError):
            clean_extra_amt = 0.0
        if clean_extra_amt < 0:
            clean_extra_amt = 0.0

        # Get old products in this invoice
        cursor.execute("SELECT DISTINCT product_norm FROM invoice_items WHERE invoice_number = ?", (clean_inv_num,))
        old_prod_norms = [r[0] for r in cursor.fetchall()]

        # Parse new customer details
        new_c_disp = " ".join(str(customer.get('shopName', '')).strip().split())
        new_c_norm = normalize_text(new_c_disp)
        new_area = " ".join(str(customer.get('area', '')).strip().split())

        # Parse new items
        new_items = []
        calc_qty = 0.0
        calc_total = 0.0
        new_prod_norms = []
        for idx, p in enumerate(products):
            p_name = " ".join(str(p.get('name') or p.get('productName') or '').strip().split())
            p_norm = normalize_text(p_name)
            if not p_name:
                continue
            try:
                qty = float(p.get('quantity', 1.0))
            except (ValueError, TypeError):
                qty = 1.0
            try:
                price_val = p.get('price') if p.get('price') is not None else p.get('unitPrice', 0.0)
                price = float(price_val if price_val is not None else 0.0)
            except (ValueError, TypeError):
                price = 0.0

            line_tot = round(qty * price, 2)
            calc_qty += qty
            calc_total += line_tot
            new_items.append((p_norm, p_name, qty, price, line_tot, idx + 1))
            if p_norm not in new_prod_norms:
                new_prod_norms.append(p_norm)

        subtotal = round(calc_total, 2)
        final_total = round(subtotal + clean_extra_amt, 2)
        f_path = str(new_file_path or old_fpath or '')
        f_name = str(new_filename or old_fname or '')
        now_iso = datetime.now().isoformat()

        # 1. Update invoices table
        cursor.execute("""
            UPDATE invoices
            SET customer_norm = ?,
                customer_display = ?,
                area = ?,
                invoice_type = ?,
                product_count = ?,
                total_quantity = ?,
                total_amount = ?,
                file_path = ?,
                filename = ?,
                extra_charges_desc = ?,
                extra_charges_amount = ?,
                updated_at = ?
            WHERE invoice_number = ?
        """, (
            new_c_norm, new_c_disp, new_area, invoice_type,
            len(new_items), calc_qty, final_total,
            f_path, f_name, clean_extra_desc, clean_extra_amt,
            now_iso, clean_inv_num
        ))

        # 2. Replace items in invoice_items
        cursor.execute("DELETE FROM invoice_items WHERE invoice_number = ?", (clean_inv_num,))
        for p_norm, p_name, qty, price, line_tot, order_idx in new_items:
            cursor.execute("""
                INSERT INTO invoice_items (
                    invoice_number, customer_norm, product_norm, product_display,
                    quantity, price, total_amount, item_order
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (clean_inv_num, new_c_norm, p_norm, p_name, qty, price, line_tot, order_idx))

        # 3. Ensure customer catalog record exists / is updated
        cursor.execute("SELECT id FROM customers WHERE normalized_name = ?", (new_c_norm,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO customers (normalized_name, display_name, area, usage_count, last_used_date, recent_invoice_number)
                VALUES (?, ?, ?, 1, ?, ?)
            """, (new_c_norm, new_c_disp, new_area, now_iso, clean_inv_num))
        else:
            cursor.execute("""
                UPDATE customers
                SET display_name = ?, area = ?
                WHERE normalized_name = ?
            """, (new_c_disp, new_area, new_c_norm))

        # 4. Ensure all product catalog records exist
        for p_norm, p_name, qty, price, line_tot, order_idx in new_items:
            cursor.execute("SELECT id FROM products WHERE normalized_name = ?", (p_norm,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO products (normalized_name, display_name, latest_price, usage_count, last_used_date, recent_invoice_number)
                    VALUES (?, ?, ?, 1, ?, ?)
                """, (p_norm, p_name, price, now_iso, clean_inv_num))

        # 5. Recalculate customer metrics (for both old and new customers)
        affected_custs = list(set([old_c_norm, new_c_norm]))
        for c_n in affected_custs:
            cursor.execute("""
                SELECT COUNT(*), COALESCE(MAX(invoice_date), '')
                FROM invoices
                WHERE customer_norm = ?
            """, (c_n,))
            rem_invs, cust_last_dt = cursor.fetchone()
            cursor.execute("""
                UPDATE customers
                SET usage_count = ?, last_used_date = CASE WHEN ? != '' THEN ? ELSE last_used_date END
                WHERE normalized_name = ?
            """, (rem_invs, cust_last_dt, cust_last_dt, c_n))

        # 6. Recalculate product metrics for all affected products
        all_affected_prods = list(set(old_prod_norms + new_prod_norms))
        for p_n in all_affected_prods:
            cursor.execute("""
                SELECT COUNT(DISTINCT ii.invoice_number), COALESCE(MAX(i.invoice_date), ''), COALESCE(MAX(ii.price), 0)
                FROM invoice_items ii
                JOIN invoices i ON ii.invoice_number = i.invoice_number
                WHERE ii.product_norm = ?
            """, (p_n,))
            p_count, p_last_dt, p_latest_price = cursor.fetchone()
            cursor.execute("""
                UPDATE products
                SET usage_count = ?, 
                    last_used_date = CASE WHEN ? != '' THEN ? ELSE last_used_date END,
                    latest_price = CASE WHEN ? > 0 THEN ? ELSE latest_price END
                WHERE normalized_name = ?
            """, (p_count, p_last_dt, p_last_dt, p_latest_price, p_latest_price, p_n))

        # 7. Recalculate customer_purchases pairs
        affected_pairs = set()
        for p_n in old_prod_norms:
            affected_pairs.add((old_c_norm, p_n))
        for p_n in new_prod_norms:
            affected_pairs.add((new_c_norm, p_n))

        for c_n, p_n in affected_pairs:
            cursor.execute("""
                SELECT COUNT(DISTINCT ii.invoice_number), COALESCE(SUM(ii.quantity), 0), 
                       COALESCE(MAX(ii.price), 0), COALESCE(MAX(i.invoice_date), ''),
                       COALESCE(MAX(ii.product_display), ''), COALESCE(MAX(i.customer_display), '')
                FROM invoice_items ii
                JOIN invoices i ON ii.invoice_number = i.invoice_number
                WHERE ii.customer_norm = ? AND ii.product_norm = ?
            """, (c_n, p_n))
            agg = cursor.fetchone()
            rem_count, rem_qty, last_pr, last_dt, p_disp, c_disp = agg
            if rem_count > 0:
                cursor.execute("""
                    INSERT INTO customer_purchases (
                        customer_norm, customer_display, product_norm, product_display,
                        order_count, total_quantity, last_price, last_ordered_date, recent_invoice_number
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(customer_norm, product_norm) DO UPDATE SET
                        order_count = excluded.order_count,
                        total_quantity = excluded.total_quantity,
                        last_price = excluded.last_price,
                        last_ordered_date = excluded.last_ordered_date,
                        recent_invoice_number = excluded.recent_invoice_number,
                        customer_display = excluded.customer_display,
                        product_display = excluded.product_display
                """, (c_n, c_disp, p_n, p_disp, rem_count, rem_qty, last_pr, last_dt, clean_inv_num))
            else:
                cursor.execute("DELETE FROM customer_purchases WHERE customer_norm = ? AND product_norm = ?", (c_n, p_n))

        # 8. Record in invoice_edit_history (audit log)
        summary_parts = []
        if old_c_disp != new_c_disp:
            summary_parts.append(f"Customer changed from '{old_c_disp}' to '{new_c_disp}'")
        if old_area != new_area:
            summary_parts.append(f"Area changed from '{old_area}' to '{new_area}'")
        if old_tot != final_total:
            summary_parts.append(f"Total changed from ₹{old_tot} to ₹{final_total}")
        if (old_extra_amt != clean_extra_amt) or (old_extra_desc != clean_extra_desc):
            summary_parts.append(f"Extra charges changed to '{clean_extra_desc}' (₹{clean_extra_amt})")
        summary_parts.append(f"Line items count: {len(new_items)}")
        summary_str = "; ".join(summary_parts)

        cursor.execute("""
            INSERT INTO invoice_edit_history (
                invoice_number, edited_at, old_customer, new_customer, old_total, new_total, changes_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (clean_inv_num, now_iso, old_c_disp, new_c_disp, old_tot, final_total, summary_str))

        # 9. Update processed_invoices
        if f_name:
            cursor.execute("""
                INSERT INTO processed_invoices (invoice_file, customer_norm, processed_at)
                VALUES (?, ?, ?)
                ON CONFLICT(invoice_file) DO UPDATE SET
                    customer_norm = excluded.customer_norm,
                    processed_at = excluded.processed_at
            """, (f_name, new_c_norm, now_iso))

        conn.commit()

    # Fetch updated details
    updated_detail = get_invoice_detail(clean_inv_num)
    return updated_detail

def get_invoice_edit_history(invoice_number: str):
    """Retrieve audit log of edits for a specific invoice."""
    init_db()
    if not invoice_number:
        return []
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, invoice_number, edited_at, old_customer, new_customer, old_total, new_total, changes_summary
            FROM invoice_edit_history
            WHERE invoice_number = ?
            ORDER BY edited_at DESC
        """, (str(invoice_number).strip(),))
        rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "invoiceNumber": r[1],
                "editedAt": r[2],
                "oldCustomer": r[3],
                "newCustomer": r[4],
                "oldTotal": r[5],
                "newTotal": r[6],
                "summary": r[7]
            }
            for r in rows
        ]

def get_customer_delete_preview(customer_name: str, storage_dir=None):
    """Get preview details for deleting a customer."""
    init_db()
    c_norm = normalize_text(customer_name)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT display_name, area FROM customers WHERE normalized_name = ?", (c_norm,))
        cust_row = cursor.fetchone()
        display_name = cust_row[0] if cust_row else customer_name
        area = cust_row[1] if cust_row else ""
        
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(total_amount), 0) FROM invoices WHERE customer_norm = ?", (c_norm,))
        inv_count, total_amt = cursor.fetchone()
        
    folder_exists = False
    folder_name = ""
    if storage_dir:
        s_path = Path(storage_dir).resolve()
        if s_path.exists():
            for d in s_path.iterdir():
                if d.is_dir() and normalize_text(d.name) == c_norm:
                    folder_exists = True
                    folder_name = d.name
                    break
                
    return {
        "customerName": display_name,
        "area": area,
        "invoiceCount": inv_count,
        "totalAmount": round(total_amt, 2),
        "hasFolder": folder_exists,
        "folderName": folder_name
    }

def remove_customer_from_catalog(customer_name: str):
    """
    Mode 1: Remove customer from suggestions/catalog only.
    Preserves all past invoices, files, and historical totals.
    """
    init_db()
    c_norm = normalize_text(customer_name)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT display_name FROM customers WHERE normalized_name = ?", (c_norm,))
        row = cursor.fetchone()
        display_name = row[0] if row else customer_name
        
        cursor.execute("DELETE FROM customers WHERE normalized_name = ?", (c_norm,))
        conn.commit()
        
    return {
        "customerName": display_name,
        "mode": "catalog"
    }

def permanently_delete_customer_all_data(customer_name: str, storage_dir=None):
    """
    Mode 2: Permanently delete customer profile, all their invoices,
    their dedicated folder in Invoice Storage, and recalculate statistics.
    """
    init_db()
    c_norm = normalize_text(customer_name)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT display_name FROM customers WHERE normalized_name = ?", (c_norm,))
        row = cursor.fetchone()
        display_name = row[0] if row else customer_name
        
        # Get all invoice numbers for this customer
        cursor.execute("SELECT invoice_number, filename, file_path FROM invoices WHERE customer_norm = ?", (c_norm,))
        inv_rows = cursor.fetchall()
        inv_numbers = [r[0] for r in inv_rows]
        
        # Get affected products to update their usage count later
        cursor.execute("""
            SELECT DISTINCT product_norm
            FROM invoice_items
            WHERE customer_norm = ?
        """, (c_norm,))
        affected_prods = [r[0] for r in cursor.fetchall()]
        
        # Delete invoice_items
        cursor.execute("DELETE FROM invoice_items WHERE customer_norm = ?", (c_norm,))
        # Delete customer_purchases
        cursor.execute("DELETE FROM customer_purchases WHERE customer_norm = ?", (c_norm,))
        # Delete invoices
        cursor.execute("DELETE FROM invoices WHERE customer_norm = ?", (c_norm,))
        # Delete customer
        cursor.execute("DELETE FROM customers WHERE normalized_name = ?", (c_norm,))
        
        # Delete from processed_invoices
        for _, fname, fpath in inv_rows:
            cursor.execute("DELETE FROM processed_invoices WHERE invoice_file = ? OR invoice_file = ?", (fname, fpath))
            
        # Update usage counts for affected products
        for p_norm in affected_prods:
            cursor.execute("""
                SELECT COUNT(DISTINCT ii.invoice_number), COALESCE(MAX(i.invoice_date), '')
                FROM invoice_items ii
                JOIN invoices i ON ii.invoice_number = i.invoice_number
                WHERE ii.product_norm = ?
            """, (p_norm,))
            prod_agg = cursor.fetchone()
            p_count, p_last_dt = prod_agg
            cursor.execute("""
                UPDATE products
                SET usage_count = ?, last_used_date = CASE WHEN ? != '' THEN ? ELSE last_used_date END
                WHERE normalized_name = ?
            """, (p_count, p_last_dt, p_last_dt, p_norm))
            
        conn.commit()
        
    # Delete customer folder and files from disk safely
    deleted_folder = False
    if storage_dir:
        s_path = Path(storage_dir).resolve()
        if s_path.exists():
            for d in s_path.iterdir():
                if d.is_dir() and normalize_text(d.name) == c_norm and d.resolve().is_relative_to(s_path):
                    try:
                        shutil.rmtree(d)
                        deleted_folder = True
                        print(f"🗑️ Deleted customer folder: {d}")
                    except Exception as e:
                        print(f"Error removing customer folder {d}: {e}")
                    
    return {
        "customerName": display_name,
        "deletedInvoicesCount": len(inv_numbers),
        "deletedFolder": deleted_folder,
        "mode": "permanent"
    }

def get_product_delete_preview(product_name: str):
    """Get preview of affected invoices and sales for a product."""
    init_db()
    p_norm = normalize_text(product_name)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT display_name, latest_price FROM products WHERE normalized_name = ?", (p_norm,))
        p_row = cursor.fetchone()
        display_name = p_row[0] if p_row else product_name
        latest_price = p_row[1] if p_row else 0.0
        
        cursor.execute("""
            SELECT ii.invoice_number, i.customer_display, i.invoice_date, ii.quantity, ii.price, ii.total_amount
            FROM invoice_items ii
            JOIN invoices i ON ii.invoice_number = i.invoice_number
            WHERE ii.product_norm = ?
            ORDER BY i.invoice_date DESC
        """, (p_norm,))
        rows = cursor.fetchall()
        
        invoices = []
        total_qty = 0.0
        total_sales = 0.0
        for r in rows:
            total_qty += r[3]
            total_sales += r[5]
            invoices.append({
                "invoiceNumber": r[0],
                "customerName": r[1],
                "date": format_date_display(r[2]),
                "quantity": r[3],
                "price": r[4],
                "totalAmount": r[5]
            })
            
    return {
        "productName": display_name,
        "latestPrice": latest_price,
        "totalInvoices": len(invoices),
        "totalQuantity": total_qty,
        "totalSales": round(total_sales, 2),
        "affectedInvoices": invoices[:15]
    }

def remove_product_from_catalog(product_name: str):
    """
    Mode 1: Remove product from catalog/autocomplete only.
    Preserves all past invoices, line items, and sales records.
    """
    init_db()
    p_norm = normalize_text(product_name)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT display_name FROM products WHERE normalized_name = ?", (p_norm,))
        row = cursor.fetchone()
        display_name = row[0] if row else product_name
        
        cursor.execute("DELETE FROM products WHERE normalized_name = ?", (p_norm,))
        conn.commit()
        
    return {
        "productName": display_name,
        "mode": "catalog"
    }

def permanently_delete_product_all_data(product_name: str, storage_dir=None):
    """
    Mode 2: Permanently delete product from catalog, customer purchases,
    and remove product line items from invoices, updating invoice totals.
    If an invoice had only this product, delete that invoice.
    """
    init_db()
    p_norm = normalize_text(product_name)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT display_name FROM products WHERE normalized_name = ?", (p_norm,))
        row = cursor.fetchone()
        display_name = row[0] if row else product_name
        
        # 1. Delete from products table
        cursor.execute("DELETE FROM products WHERE normalized_name = ?", (p_norm,))
        
        # 2. Delete from customer_purchases
        cursor.execute("DELETE FROM customer_purchases WHERE product_norm = ?", (p_norm,))
        
        # 3. Find invoices containing this product
        cursor.execute("SELECT DISTINCT invoice_number FROM invoice_items WHERE product_norm = ?", (p_norm,))
        affected_invs = [r[0] for r in cursor.fetchall()]
        
        # 4. Remove item from invoice_items
        cursor.execute("DELETE FROM invoice_items WHERE product_norm = ?", (p_norm,))
        
        empty_invoices = []
        # 5. Check affected invoices
        for inv_num in affected_invs:
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(quantity), 0), COALESCE(SUM(total_amount), 0) FROM invoice_items WHERE invoice_number = ?", (inv_num,))
            rem_items, rem_qty, rem_amt = cursor.fetchone()
            if rem_items == 0:
                empty_invoices.append(inv_num)
            else:
                cursor.execute("""
                    UPDATE invoices
                    SET product_count = ?, total_quantity = ?, total_amount = ?
                    WHERE invoice_number = ?
                """, (rem_items, rem_qty, rem_amt, inv_num))
                
        conn.commit()

    # Safely delete any invoices that became empty outside the active write transaction
    for empty_inv in empty_invoices:
        delete_invoice_by_number(empty_inv, storage_dir=storage_dir)
        
    return {
        "productName": display_name,
        "affectedInvoicesCount": len(affected_invs),
        "mode": "permanent"
    }

# Initialize DB when module loads
init_db()

