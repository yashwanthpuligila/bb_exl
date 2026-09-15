from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
import re
import sqlite3
from pathlib import Path
from datetime import datetime
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
import tempfile
import json
import glob
import time
import threading
from recommendation_engine import recommendation_engine
import learning_db
import shutil

# Paths based on script location
WEB_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = WEB_DIR.parent
if (PROJECT_ROOT / "Invoice Storage").exists() or (PROJECT_ROOT / "web").exists():
    INVOICE_STORAGE_DIR = (PROJECT_ROOT / "Invoice Storage").resolve()
else:
    INVOICE_STORAGE_DIR = (WEB_DIR / "Invoice Storage").resolve()
INVOICE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize recommendation engine on startup
@app.before_request
def initialize_recommendations():
    """Initialize ML recommendation engine and learning DB with historical data"""
    if not hasattr(app, 'recommendations_loaded'):
        print("🤖 Loading ML recommendation engine...")
        recommendation_engine.load_data_from_invoices(str(WEB_DIR))
        recommendation_engine.load_data_from_invoices(str(PROJECT_ROOT))
        if INVOICE_STORAGE_DIR.exists():
            recommendation_engine.load_data_from_invoices(str(INVOICE_STORAGE_DIR))
        
        # Initialize learning db from historical invoices
        try:
            dirs_to_check = [str(WEB_DIR), str(PROJECT_ROOT)]
            if INVOICE_STORAGE_DIR.exists():
                dirs_to_check.append(str(INVOICE_STORAGE_DIR))
            learning_db.import_historical_data(dirs_to_check)
            print("🧠 Customer and product learning database initialized.")
        except Exception as e:
            print(f"Error initializing learning DB: {e}")

        app.recommendations_loaded = True

@app.route('/')
def index():
    """Serve the main page"""
    return send_file(WEB_DIR / 'index.html')

@app.route('/styles.css')
def styles():
    """Serve CSS file"""
    return send_file(WEB_DIR / 'styles.css', mimetype='text/css')

@app.route('/script.js')
def script():
    """Serve JavaScript file"""
    return send_file(WEB_DIR / 'script.js', mimetype='application/javascript')

@app.route('/manifest.json')
def manifest():
    """Serve PWA manifest"""
    return send_file(WEB_DIR / 'manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def service_worker():
    """Serve PWA service worker"""
    return send_file(WEB_DIR / 'sw.js', mimetype='application/javascript')

@app.route('/icons/<path:filename>')
def serve_icon(filename):
    """Serve PWA icons"""
    icons_dir = WEB_DIR / 'icons'
    return send_from_directory(str(icons_dir), filename)

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    return send_file(WEB_DIR / 'icons' / 'favicon.png', mimetype='image/png')

@app.route('/api/generate-invoice', methods=['POST'])
def generate_invoice():
    """Generate Excel invoice from JSON data"""
    try:
        data = request.get_json()
        
        # Validate required data
        if not data or 'customer' not in data or 'products' not in data:
            return jsonify({'error': 'Invalid data provided'}), 400
        
        customer = data['customer']
        products = data['products']
        invoice_type = data.get('invoiceType') or data.get('invoice_type', 'current')  # 'current' or 'all'

        
        # Validate customer data
        required_fields = ['shopName', 'area']
        for field in required_fields:
            if not customer.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        if not products:
            return jsonify({'error': 'No products provided'}), 400
        
        # Extra charges extraction and validation
        extra_charges_desc = str(data.get('extraChargesDesc') or data.get('extra_charges_desc') or '').strip()
        raw_extra_amt = data.get('extraChargesAmount') if data.get('extraChargesAmount') is not None else data.get('extra_charges_amount', 0.0)
        try:
            extra_charges_amount = float(raw_extra_amt or 0.0)
            if extra_charges_amount < 0:
                return jsonify({'error': 'Extra charges amount cannot be negative'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid extra charges amount format'}), 400

        # Generate invoice number
        invoice_number = generate_invoice_number()
        
        # Create Excel file and get history data
        filename, history_data = create_excel_invoice(
            customer, products, invoice_number, invoice_type,
            extra_charges_desc=extra_charges_desc,
            extra_charges_amount=extra_charges_amount
        )
        
        # Immediately record customer, products, and full invoice in learning database
        try:
            shop_name = customer.get('shopName', '').strip()
            customer_dir = get_or_create_customer_dir(shop_name)
            full_path = str(customer_dir / filename)
            learning_db.record_invoice(
                invoice_number=invoice_number,
                customer_name=shop_name,
                area=customer.get('area', ''),
                products=products,
                invoice_type=invoice_type,
                invoice_date=datetime.now(),
                total_amount=history_data.get('grand_total'),
                file_path=full_path,
                filename=filename,
                extra_charges_desc=extra_charges_desc,
                extra_charges_amount=extra_charges_amount
            )
        except Exception as learn_err:
            print(f"Error learning invoice: {learn_err}")

        return jsonify({
            'success': True,
            'filename': filename,
            'invoice_number': invoice_number,
            'download_url': f'/api/download/{filename}',
            'history': history_data
        })
        
    except Exception as e:
        print(f"Error generating invoice: {str(e)}")
        return jsonify({'error': f'Error generating invoice: {str(e)}'}), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    """Download generated Excel file safely, regenerating from DB if disk was cleared"""
    try:
        safe_name = os.path.basename(filename)
        # Check temp directory first
        temp_file = Path(tempfile.gettempdir()) / safe_name
        if temp_file.exists() and temp_file.is_file():
            return send_file(
                str(temp_file), 
                as_attachment=True,
                download_name=safe_name,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        
        # Search inside INVOICE_STORAGE_DIR safely
        if INVOICE_STORAGE_DIR.exists():
            for p in INVOICE_STORAGE_DIR.rglob(safe_name):
                if p.is_file() and p.resolve().is_relative_to(INVOICE_STORAGE_DIR):
                    return send_file(
                        str(p),
                        as_attachment=True,
                        download_name=safe_name,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    
        # If not on disk (e.g. Render restart on ephemeral storage), regenerate from database
        try:
            inv_match = re.search(r'(INV-\d{8}-\d{6}-\d{3})', safe_name)
            inv_num = inv_match.group(1) if inv_match else safe_name.replace('.xlsx', '')
            detail = learning_db.get_invoice_detail(inv_num)
            if detail:
                customer_data = {
                    'shopName': detail.get('customerName', ''),
                    'area': detail.get('area', '')
                }
                products_data = detail.get('products', [])
                inv_date = detail.get('date')
                inv_type = detail.get('invoiceType', 'current')
                extra_desc = detail.get('extraChargesDesc', '')
                extra_amt = detail.get('extraChargesAmount', 0.0)
                
                regen_filename, _ = create_excel_invoice(
                    customer=customer_data,
                    products=products_data,
                    invoice_number=inv_num,
                    invoice_type=inv_type,
                    invoice_date=inv_date,
                    is_edit=False,
                    extra_charges_desc=extra_desc,
                    extra_charges_amount=extra_amt
                )
                regen_path = Path(tempfile.gettempdir()) / regen_filename
                if regen_path.exists():
                    return send_file(
                        str(regen_path),
                        as_attachment=True,
                        download_name=safe_name,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
        except Exception as regen_err:
            print(f"Notice: Could not regenerate invoice from DB: {regen_err}")

        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Error downloading file: {str(e)}'}), 500


@app.route('/api/recommendations', methods=['POST'])
def get_recommendations():
    """Get ML-based product recommendations"""
    try:
        data = request.get_json()
        shop_name = data.get('shopName', '').strip()
        current_products = data.get('currentProducts', [])
        method = data.get('method', 'hybrid')
        top_n = data.get('topN', 5)
        
        # Get recommendations from ML engine
        recommendations = recommendation_engine.get_recommendations(
            customer_name=shop_name if shop_name else None,
            current_products=[p['name'] for p in current_products] if current_products else None,
            method=method,
            top_n=top_n
        )
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'count': len(recommendations)
        })
        
    except Exception as e:
        print(f"Error getting recommendations: {str(e)}")
        return jsonify({'error': f'Error getting recommendations: {str(e)}'}), 500

@app.route('/api/customer-insights/<customer_name>')
def get_customer_insights(customer_name):
    """Get insights about a specific customer"""
    try:
        insights = recommendation_engine.get_customer_insights(customer_name)
        
        if insights:
            return jsonify({
                'success': True,
                'insights': insights
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No data found for this customer'
            })
            
    except Exception as e:
        print(f"Error getting customer insights: {str(e)}")
        return jsonify({'error': f'Error getting insights: {str(e)}'}), 500

@app.route('/api/trending-products')
def get_trending_products():
    """Get trending products"""
    try:
        days = int(request.args.get('days', 30))
        top_n = int(request.args.get('topN', 10))
        
        trending = recommendation_engine.get_trending_products(days=days, top_n=top_n)
        
        return jsonify({
            'success': True,
            'trending': trending,
            'count': len(trending)
        })
        
    except Exception as e:
        print(f"Error getting trending products: {str(e)}")
        return jsonify({'error': f'Error getting trending products: {str(e)}'}), 500

@app.route('/api/reload-recommendations', methods=['POST'])
def reload_recommendations():
    """Reload recommendation engine with latest data"""
    try:
        recommendation_engine.load_data_from_invoices('.')
        recommendation_engine.load_data_from_invoices('..')
        
        dirs_to_check = ['.', '..']
        if INVOICE_STORAGE_DIR.exists():
            dirs_to_check.append(str(INVOICE_STORAGE_DIR))
        learning_db.import_historical_data(dirs_to_check, force_rebuild=True)
        
        return jsonify({
            'success': True,
            'message': 'Recommendations and learning database reloaded successfully'
        })
        
    except Exception as e:
        print(f"Error reloading recommendations: {str(e)}")
        return jsonify({'error': f'Error reloading: {str(e)}'}), 500

@app.route('/api/customer-recommendations')
def customer_recommendations():
    """Get customer-specific product recommendations based on their own order history"""
    try:
        shop_name = request.args.get('shopName', '').strip()
        limit = int(request.args.get('limit', 8))
        data = learning_db.get_customer_recommendations(shop_name, limit=limit)
        return jsonify({
            'success': True,
            **data
        })
    except Exception as e:
        print(f"Error getting customer recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rebuild-learning-data', methods=['POST', 'GET'])
def rebuild_learning_data():
    """Rebuild learning database from existing invoice files"""
    try:
        dirs_to_check = ['.', '..']
        if INVOICE_STORAGE_DIR.exists():
            dirs_to_check.append(str(INVOICE_STORAGE_DIR))
        stats = learning_db.import_historical_data(dirs_to_check, force_rebuild=True)
        return jsonify({
            'success': True,
            'message': 'Learning data rebuilt successfully',
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/autocomplete/customers')
def autocomplete_customers():
    """Autocomplete suggestions for customers"""
    try:
        q = request.args.get('q', '').strip()
        if not q:
            return jsonify({'success': True, 'customers': []})
        results = learning_db.search_customers(q, limit=10)
        return jsonify({'success': True, 'customers': results})
    except Exception as e:
        print(f"Error in autocomplete_customers: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/autocomplete/products')
def autocomplete_products():
    """Autocomplete suggestions for products"""
    try:
        q = request.args.get('q', '').strip()
        if not q:
            return jsonify({'success': True, 'products': []})
        results = learning_db.search_products(q, limit=10)
        return jsonify({'success': True, 'products': results})
    except Exception as e:
        print(f"Error in autocomplete_products: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def get_system_status():
    """Return database engine and environment status"""
    return jsonify({
        'success': True,
        'app_name': 'Sri Laxmi Gayatri Traders - Invoice ERP',
        'engine': learning_db.get_database_engine_name(),
        'is_postgres': learning_db.is_postgres(),
        'platform': 'Render Production' if learning_db.is_postgres() else 'Local Windows Desktop',
        'desktop_mode': os.environ.get('DESKTOP_MODE') == '1'
    })

_last_desktop_heartbeat = time.time()
_desktop_client_connected = False
_shutdown_timer = None
_shutdown_lock = threading.Lock()

def _schedule_graceful_shutdown(delay=2.0):
    global _shutdown_timer
    with _shutdown_lock:
        if _shutdown_timer is not None:
            _shutdown_timer.cancel()
        print(f"⏱️ Desktop shutdown scheduled in {delay}s...")
        def _do_exit():
            print("🛑 Desktop shutdown confirmed. Cleanly stopping backend...")
            os._exit(0)
        _shutdown_timer = threading.Timer(delay, _do_exit)
        _shutdown_timer.daemon = True
        _shutdown_timer.start()

def _cancel_scheduled_shutdown():
    global _shutdown_timer
    with _shutdown_lock:
        if _shutdown_timer is not None:
            print("🔄 Desktop client reconnected. Cancelling scheduled shutdown.")
            _shutdown_timer.cancel()
            _shutdown_timer = None

@app.route('/api/desktop/heartbeat', methods=['GET', 'POST'])
def desktop_heartbeat():
    """Receive heartbeat pings from desktop frontend"""
    global _last_desktop_heartbeat, _desktop_client_connected
    _last_desktop_heartbeat = time.time()
    _desktop_client_connected = True
    _cancel_scheduled_shutdown()
    return jsonify({'status': 'ok', 'timestamp': _last_desktop_heartbeat})

@app.route('/api/desktop/shutdown', methods=['GET', 'POST'])
def desktop_shutdown():
    """Trigger graceful backend shutdown from desktop client"""
    if os.environ.get('DESKTOP_MODE') == '1':
        _schedule_graceful_shutdown(delay=2.0)
    return jsonify({'status': 'shutdown_scheduled'})

def _start_desktop_watchdog():
    if os.environ.get('DESKTOP_MODE') == '1':
        def _watchdog_loop():
            # Allow up to 45 seconds on cold start for initial frontend connection
            for _ in range(45):
                time.sleep(1)
                if _desktop_client_connected:
                    break
            while True:
                time.sleep(2)
                # If desktop window connected then went silent for > 8s, cleanly exit
                if _desktop_client_connected and (time.time() - _last_desktop_heartbeat > 8):
                    print("⚠️ Desktop client disconnected. Stopping backend process...")
                    os._exit(0)
        watchdog = threading.Thread(target=_watchdog_loop, daemon=True)
        watchdog.start()

_start_desktop_watchdog()

@app.route('/api/stats')
def get_stats():
    """Get overall system statistics"""
    try:
        total_customers = len(recommendation_engine.customer_products)
        total_products = len(recommendation_engine.product_popularity)
        total_orders = sum(recommendation_engine.product_popularity.values())
        
        return jsonify({
            'success': True,
            'engine': learning_db.get_database_engine_name(),
            'stats': {
                'total_customers': total_customers,
                'total_products': total_products,
                'total_orders': total_orders
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard')
def get_dashboard():
    """Get dashboard analytics, metrics, chart data, and recent invoices from real saved invoices"""
    try:
        date_range = request.args.get('range', '30d')
        data = learning_db.get_dashboard_analytics(date_range)
        return jsonify({
            'success': True,
            'engine': learning_db.get_database_engine_name(),
            **data
        })
    except Exception as e:
        print(f"Error getting dashboard data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices')
def get_invoices():
    """Get searchable, filterable, sortable invoices list"""
    try:
        q = request.args.get('q', '').strip()
        customer = request.args.get('customer', '').strip()
        date_range = request.args.get('range', 'all').strip()
        type_filter = request.args.get('type', '').strip()
        sort_by = request.args.get('sort_by', 'date').strip()
        sort_order = request.args.get('sort_order', 'desc').strip()
        limit = int(request.args.get('limit', 100))
        
        data = learning_db.get_all_invoices(
            q=q, customer=customer, date_range=date_range,
            type_filter=type_filter, sort_by=sort_by, sort_order=sort_order,
            limit=limit
        )
        return jsonify({
            'success': True,
            **data
        })
    except Exception as e:
        print(f"Error getting invoices: {e}")
        return jsonify({'error': str(e)}), 500

# Note: GET and DELETE /api/invoices/<invoice_number> are handled by invoice_detail_or_delete_route below

@app.route('/api/customers')
def get_customers():
    """Get all customers with aggregate metrics"""
    try:
        q = request.args.get('q', '').strip()
        sort_by = request.args.get('sort_by', 'amount').strip()
        customers = learning_db.get_customers_overview(q=q, sort_by=sort_by)
        return jsonify({
            'success': True,
            'customers': customers,
            'totalCount': len(customers)
        })
    except Exception as e:
        print(f"Error getting customers: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/customers/<customer_name>')
def get_customer_profile_route(customer_name):
    """Get detailed customer profile with order history and recommendations"""
    try:
        profile = learning_db.get_customer_profile(customer_name)
        if not profile:
            return jsonify({'error': 'Customer not found'}), 404
        return jsonify({
            'success': True,
            'customer': profile
        })
    except Exception as e:
        print(f"Error getting customer profile: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/products')
def get_products():
    """Get all products with aggregate sales and pricing stats"""
    try:
        q = request.args.get('q', '').strip()
        sort_by = request.args.get('sort_by', 'quantity').strip()
        products = learning_db.get_products_overview(q=q, sort_by=sort_by)
        return jsonify({
            'success': True,
            'products': products,
            'totalCount': len(products)
        })
    except Exception as e:
        print(f"Error getting products: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/<product_name>')
def get_product_profile_route(product_name):
    """Get product profile with buyers, price history, and recent sales"""
    try:
        profile = learning_db.get_product_profile(product_name)
        if not profile:
            return jsonify({'error': 'Product not found'}), 404
        return jsonify({
            'success': True,
            'product': profile
        })
    except Exception as e:
        print(f"Error getting product profile: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/sales')
def get_sales_analytics():
    """Get sales analytics chart data"""
    try:
        date_range = request.args.get('range', '30d')
        data = learning_db.get_dashboard_analytics(date_range)
        return jsonify({
            'success': True,
            'chart': data.get('chart', {})
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/export-db', methods=['GET'])
def export_database():
    """Download local SQLite database file for backup on Desktop"""
    try:
        if learning_db.is_postgres():
            return jsonify({
                'success': True,
                'message': 'Application is running on Render PostgreSQL. Data is securely saved in the cloud.',
                'engine': 'PostgreSQL'
            })

        db_path = learning_db.DB_PATH
        if db_path.exists():
            # Checkpoint WAL buffer to ensure db file has all updates
            try:
                with learning_db.get_connection() as conn:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception as cp_err:
                print(f"Notice: Checkpoint before export: {cp_err}")

            return send_file(
                str(db_path),
                as_attachment=True,
                download_name='invoice_learning.db',
                mimetype='application/x-sqlite3'
            )
        else:
            return jsonify({'error': 'Local SQLite database file not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to export database: {str(e)}'}), 500

@app.route('/api/admin/raw-database')
def get_raw_database():
    """Return raw table schema and rows for database viewer (PostgreSQL or SQLite)"""
    try:
        selected_table = request.args.get('table', 'invoices')
        res = learning_db.get_database_tables_and_rows(selected_table=selected_table, limit=250)
        return jsonify(res)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/reset-preview')
def reset_preview():
    """Get dynamic preview counts of data that will be deleted"""
    try:
        preview = learning_db.get_reset_preview(storage_dir=str(INVOICE_STORAGE_DIR))
        return jsonify({
            'success': True,
            'preview': preview
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/reset-all-data', methods=['POST'])
def reset_all_data():
    """
    Permanently delete all generated business data:
    - All invoices and line items
    - All customer and product records
    - All customer-wise invoice folders
    - All invoice history
    - All recommendation/training data
    - All dashboard statistics data
    - All autocomplete data
    Strictly preserves source code, HTML, CSS, JS, Python, requirements, docx, templates, and git files.
    Requires exact confirmation: 'DELETE ALL DATA'
    """
    try:
        data = request.get_json(silent=True) or {}
        confirmation = (data.get('confirmation') or data.get('confirm') or '').strip()
        
        if confirmation != 'DELETE ALL DATA':
            return jsonify({
                'error': 'Confirmation text does not match. You must enter "DELETE ALL DATA" to proceed.'
            }), 400
            
        deleted_invoices_count = 0
        deleted_folders_count = 0
        
        # 1. Reset SQLite Database tables (invoices, customers, products, customer_purchases, invoice_items, processed_invoices)
        learning_db.reset_all_learning_data()
        
        # 2. Reset In-Memory Recommendation Engine
        recommendation_engine.clear_data()
        
        # 3. Safely delete contents of INVOICE_STORAGE_DIR using pathlib verification
        if INVOICE_STORAGE_DIR.exists() and INVOICE_STORAGE_DIR.is_dir():
            for item in list(INVOICE_STORAGE_DIR.iterdir()):
                # Strict safety check: must be inside INVOICE_STORAGE_DIR
                if item.resolve().is_relative_to(INVOICE_STORAGE_DIR):
                    if item.is_dir():
                        # Count invoices inside this customer folder
                        for f in item.glob('*.xlsx'):
                            deleted_invoices_count += 1
                        shutil.rmtree(str(item), ignore_errors=True)
                        deleted_folders_count += 1
                    elif item.is_file() and item.suffix.lower() == '.xlsx':
                        item.unlink(missing_ok=True)
                        deleted_invoices_count += 1
                        
        # Ensure clean empty base storage directory exists
        INVOICE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        
        # 4. Safely clean up legacy generated invoice files matching pattern Invoice_*.xlsx or INV-*.xlsx
        # in web directory and project root (strictly preserving code, docx, orders.xlsx, etc.)
        project_root = INVOICE_STORAGE_DIR.parent.resolve()
        web_dir = (Path(__file__).resolve().parent).resolve()
        
        for dir_path in [web_dir, project_root]:
            if dir_path.exists() and dir_path.is_dir():
                for pat in ['INV-*.xlsx', 'Invoice_*.xlsx']:
                    for f in dir_path.glob(pat):
                        if f.is_file() and f.resolve().is_relative_to(dir_path):
                            # Ensure we NEVER delete orders.xlsx or non-invoice files
                            if f.name.startswith(('INV-', 'Invoice_')) and f.suffix.lower() == '.xlsx':
                                f.unlink(missing_ok=True)
                                deleted_invoices_count += 1
                                
        # 5. Clean up temporary invoice copies in tempdir
        temp_dir = Path(tempfile.gettempdir()).resolve()
        for pat in ['INV-*.xlsx', 'Invoice_*.xlsx']:
            for f in temp_dir.glob(pat):
                try:
                    if f.is_file() and (f.name.startswith(('INV-', 'Invoice_'))):
                        f.unlink(missing_ok=True)
                except Exception:
                    pass
                    
        return jsonify({
            'success': True,
            'message': 'All business data, customer folders, invoices, and recommendations have been permanently deleted.',
            'stats': {
                'invoicesDeleted': deleted_invoices_count,
                'foldersDeleted': deleted_folders_count,
                'totalInvoices': 0,
                'totalCustomers': 0,
                'totalProducts': 0,
                'totalSales': 0.0
            }
        })
        
    except Exception as e:
        print(f"Error resetting all data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices/<invoice_number>', methods=['GET', 'DELETE', 'PUT'])
def invoice_detail_or_delete_route(invoice_number):
    """GET single invoice details, DELETE invoice, or PUT to update existing invoice safely"""
    try:
        clean_num = str(invoice_number).strip() if invoice_number else ''
        if not clean_num or '..' in clean_num or '/' in clean_num or '\\' in clean_num:
            return jsonify({'error': 'Invalid invoice ID format'}), 400

        if request.method == 'GET':
            inv = learning_db.get_invoice_detail(clean_num)
            if not inv:
                return jsonify({'error': f'Invoice {clean_num} not found'}), 404
            return jsonify({'success': True, 'invoice': inv})

        if request.method == 'PUT':
            data = request.get_json() or {}
            customer = data.get('customer') or {}
            products = data.get('products') or []
            invoice_type = data.get('invoiceType', 'current')

            new_shop_name = str(customer.get('shopName') or data.get('customerName') or data.get('shopName') or '').strip()
            new_area = str(customer.get('area') or data.get('area') or '').strip()
            if not new_shop_name:
                return jsonify({'error': 'Customer / Shop Name cannot be blank'}), 400
            if not new_area:
                return jsonify({'error': 'Area / Location cannot be blank'}), 400
            if not products or not isinstance(products, list):
                return jsonify({'error': 'Invoice must contain at least one product'}), 400

            cleaned_prods = []
            for idx, p in enumerate(products):
                p_name = str(p.get('name') or p.get('productName') or '').strip()
                if not p_name:
                    return jsonify({'error': f'Product name cannot be empty in item #{idx+1}'}), 400
                try:
                    qty = float(p.get('quantity', 0))
                    if qty <= 0:
                        return jsonify({'error': f'Quantity must be greater than 0 for "{p_name}"'}), 400
                except (ValueError, TypeError):
                    return jsonify({'error': f'Invalid quantity for "{p_name}"'}), 400
                try:
                    price_val = p.get('price') if p.get('price') is not None else p.get('unitPrice', 0)
                    price = float(price_val if price_val is not None else 0)
                    if price < 0:
                        return jsonify({'error': f'Price cannot be negative for "{p_name}"'}), 400
                except (ValueError, TypeError):
                    return jsonify({'error': f'Invalid price for "{p_name}"'}), 400

                cleaned_prods.append({
                    'productName': p_name,
                    'name': p_name,
                    'quantity': qty,
                    'price': price,
                    'unitPrice': price
                })

            existing = learning_db.get_invoice_detail(clean_num)
            if not existing:
                return jsonify({'error': f'Invoice {clean_num} not found'}), 404

            old_customer_name = existing.get('customerName', '')
            old_filename = existing.get('filename', '')
            old_filepath = existing.get('filePath', '')
            original_date = existing.get('date')

            # Clean up old file from old customer folder if customer changed
            if old_customer_name and learning_db.normalize_text(old_customer_name) != learning_db.normalize_text(new_shop_name):
                if INVOICE_STORAGE_DIR.exists():
                    clean_old_cust = re.sub(r'[\\/*?:"<>|]', "", old_customer_name.strip())
                    old_cust_dir = (INVOICE_STORAGE_DIR / clean_old_cust).resolve()
                    if old_cust_dir.exists() and old_cust_dir.is_relative_to(INVOICE_STORAGE_DIR):
                        for stem in [clean_num, Path(old_filename).stem if old_filename else clean_num]:
                            for ext in ['.xlsx', '.xls', '.pdf']:
                                old_file = old_cust_dir / f"{stem}{ext}"
                                if old_file.exists() and old_file.is_file():
                                    try:
                                        old_file.unlink()
                                    except Exception as e:
                                        print(f"Warning cleaning old file {old_file}: {e}")

            # Extra charges extraction and validation
            extra_charges_desc = str(data.get('extraChargesDesc') if data.get('extraChargesDesc') is not None else (data.get('extra_charges_desc') or '')).strip()
            raw_extra_amt = data.get('extraChargesAmount') if data.get('extraChargesAmount') is not None else data.get('extra_charges_amount', 0.0)
            try:
                extra_charges_amount = float(raw_extra_amt or 0.0)
                if extra_charges_amount < 0:
                    return jsonify({'error': 'Extra charges amount cannot be negative'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid extra charges amount format'}), 400

            # Regenerate Excel file in updated customer folder with original date
            new_customer_obj = {'shopName': new_shop_name, 'area': new_area}
            new_filename, history_data = create_excel_invoice(
                new_customer_obj, cleaned_prods, clean_num, invoice_type,
                invoice_date=original_date, is_edit=True,
                extra_charges_desc=extra_charges_desc,
                extra_charges_amount=extra_charges_amount
            )
            new_customer_dir = get_or_create_customer_dir(new_shop_name)
            new_full_path = str(new_customer_dir / new_filename)

            # Update database records, metrics, and audit history
            updated_inv = learning_db.update_invoice_record(
                invoice_number=clean_num,
                customer=new_customer_obj,
                products=cleaned_prods,
                invoice_type=invoice_type,
                new_file_path=new_full_path,
                new_filename=new_filename,
                storage_dir=INVOICE_STORAGE_DIR,
                extra_charges_desc=extra_charges_desc,
                extra_charges_amount=extra_charges_amount
            )

            # Rebuild recommendations engine
            recommendation_engine.rebuild_from_db()

            return jsonify({
                'success': True,
                'message': f'Invoice {clean_num} updated successfully',
                'invoice': updated_inv,
                'invoice_number': clean_num,
                'filename': new_filename,
                'download_url': f'/api/download/{new_filename}'
            })

        # DELETE request
        res = learning_db.delete_invoice_by_number(clean_num, storage_dir=INVOICE_STORAGE_DIR)
        if not res:
            return jsonify({'error': f'Invoice {clean_num} not found'}), 404
            
        recommendation_engine.rebuild_from_db()
        return jsonify({
            'success': True,
            'deleted': res,
            'invoiceId': clean_num,
            'invoiceNumber': clean_num,
            'message': f'Invoice {clean_num} deleted successfully'
        })
    except Exception as e:
        print(f"Error handling invoice {invoice_number}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices/bulk-delete', methods=['POST'])
def bulk_delete_invoices_route():
    """Delete multiple selected invoices safely"""
    try:
        data = request.get_json() or {}
        raw_ids = data.get('invoiceIds')
        if raw_ids is None:
            raw_ids = data.get('invoice_numbers') or data.get('invoice_ids') or []
            
        if not raw_ids or not isinstance(raw_ids, list):
            return jsonify({'error': 'No invoice IDs provided. Please provide an "invoiceIds" array.'}), 400

        valid_ids = []
        invalid_ids = []
        for item in raw_ids:
            if not isinstance(item, (str, int)):
                invalid_ids.append(str(item))
                continue
            cleaned = str(item).strip()
            # Safety validation against directory traversal and invalid characters
            if not cleaned or '..' in cleaned or '/' in cleaned or '\\' in cleaned:
                invalid_ids.append(cleaned if cleaned else '<empty>')
                continue
            if cleaned not in valid_ids:
                valid_ids.append(cleaned)

        if not valid_ids:
            return jsonify({
                'error': 'No valid invoice IDs provided',
                'invalidIds': invalid_ids
            }), 400

        res = learning_db.bulk_delete_invoices(valid_ids, storage_dir=INVOICE_STORAGE_DIR)
        recommendation_engine.rebuild_from_db()

        total_failed_count = res.get('failedCount', 0) + len(invalid_ids)
        all_failed = res.get('failedInvoices', []) + invalid_ids

        return jsonify({
            'success': True,
            'message': f"Successfully deleted {res.get('deletedCount', 0)} invoice(s).",
            'deletedCount': res.get('deletedCount', 0),
            'deleted_count': res.get('deletedCount', 0),
            'failedCount': total_failed_count,
            'totalAmount': res.get('totalAmount', 0.0),
            'deletedInvoices': res.get('deletedInvoices', []),
            'failedInvoices': all_failed
        })
    except Exception as e:
        print(f"Error bulk deleting invoices: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/customers/<customer_name>/delete-preview', methods=['GET'])
def customer_delete_preview_route(customer_name):
    """Get preview of customer deletion impact"""
    try:
        preview = learning_db.get_customer_delete_preview(customer_name, storage_dir=INVOICE_STORAGE_DIR)
        return jsonify({
            'success': True,
            'preview': preview,
            'invoice_count': preview.get('invoiceCount', 0),
            'total_spent': preview.get('totalAmount', 0),
            'has_folder': preview.get('hasFolder', False),
            'customer_folder': f"Invoice Storage/{preview.get('folderName', customer_name)}" if preview.get('hasFolder') else f"Invoice Storage/{customer_name}",
            **preview
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/customers/<customer_name>', methods=['DELETE'])
def remove_customer_route(customer_name):
    """Mode 1: Remove customer from suggestions/catalog only"""
    try:
        res = learning_db.remove_customer_from_catalog(customer_name)
        recommendation_engine.rebuild_from_db()
        return jsonify({'success': True, 'mode': 'catalog', 'message': f'Customer "{customer_name}" removed from suggestions.', **res})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/customers/<customer_name>/all-data', methods=['DELETE', 'POST'])
def delete_customer_all_data_route(customer_name):
    """Mode 2: Permanently delete customer, all their invoices, and folder"""
    try:
        data = request.get_json(silent=True) or {}
        confirmation = (data.get('confirmation') or request.args.get('confirmation') or '').strip()
        if not confirmation or learning_db.normalize_text(confirmation) != learning_db.normalize_text(customer_name):
            return jsonify({'error': f'Confirmation does not match. Please enter "{customer_name}" to confirm.'}), 400
        res = learning_db.permanently_delete_customer_all_data(customer_name, storage_dir=INVOICE_STORAGE_DIR)
        recommendation_engine.rebuild_from_db()
        return jsonify({'success': True, 'mode': 'permanent', 'message': f'Customer "{customer_name}" and all invoice data permanently deleted.', **res})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/<product_name>/delete-preview', methods=['GET'])
def product_delete_preview_route(product_name):
    """Get preview of product deletion impact and affected invoices"""
    try:
        preview = learning_db.get_product_delete_preview(product_name)
        return jsonify({
            'success': True,
            'preview': preview,
            'affected_invoices_count': preview.get('totalInvoices', 0),
            'total_quantity_sold': preview.get('totalQuantity', 0),
            'total_sales': preview.get('totalSales', 0),
            'affected_invoices': preview.get('affectedInvoices', []),
            **preview
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/<product_name>', methods=['DELETE'])
def remove_product_route(product_name):
    """Mode 1: Remove product from catalog/autocomplete only"""
    try:
        res = learning_db.remove_product_from_catalog(product_name)
        recommendation_engine.rebuild_from_db()
        return jsonify({'success': True, 'mode': 'catalog', 'message': f'Product "{product_name}" removed from autocomplete.', **res})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/<product_name>/all-data', methods=['DELETE', 'POST'])
def delete_product_all_data_route(product_name):
    """Mode 2: Permanently delete product from catalog and related invoice references"""
    try:
        data = request.get_json(silent=True) or {}
        confirmation = (data.get('confirmation') or request.args.get('confirmation') or '').strip()
        if confirmation.upper() != "DELETE PRODUCT DATA":
            return jsonify({'error': 'Confirmation text does not match. You must enter "DELETE PRODUCT DATA" to proceed.'}), 400
        res = learning_db.permanently_delete_product_all_data(product_name, storage_dir=INVOICE_STORAGE_DIR)
        recommendation_engine.rebuild_from_db()
        return jsonify({'success': True, 'mode': 'permanent', 'message': f'Product "{product_name}" and related data permanently deleted.', **res})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


_invoice_counter = 0

def generate_invoice_number():
    """Generate unique invoice number guaranteed to be distinct even in high frequency."""
    global _invoice_counter
    now = datetime.now()
    _invoice_counter = (_invoice_counter + 1) % 1000
    return f"INV-{now.strftime('%Y%m%d-%H%M%S')}-{_invoice_counter:03d}"

def sanitize_folder_name(name: str) -> str:
    """
    Sanitize customer shop name for a clean, safe Windows directory name.
    - Collapses consecutive whitespace to a single space.
    - Strips leading and trailing spaces and dots.
    - Removes invalid Windows characters: \ / : * ? " < > | and control chars.
    - Falls back to 'Customer' if empty.
    """
    clean = " ".join(str(name).strip().split())
    clean = re.sub(r'[\\/*?:"<>|\x00-\x1f]', "", clean)
    clean = clean.strip(". ")
    return clean if clean else "Customer"

def normalize_key(name: str) -> str:
    """Normalize a customer name for case-insensitive and whitespace-collapsed comparison."""
    return " ".join(str(name).strip().lower().split())

def get_or_create_customer_dir(shop_name: str) -> Path:
    """
    Find existing customer folder matching the normalized shop name,
    or create a new one safely inside Invoice Storage.
    Treats different capitalization and extra spaces as the same customer.
    Strictly blocks path traversal and ensures boundary integrity.
    """
    INVOICE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    target_key = normalize_key(shop_name)
    
    # Check existing folders in Invoice Storage
    for entry in INVOICE_STORAGE_DIR.iterdir():
        if entry.is_dir() and normalize_key(entry.name) == target_key:
            return entry.resolve()
            
    # If no existing folder matched, create new folder with sanitized name
    clean_name = sanitize_folder_name(shop_name)
    customer_dir = (INVOICE_STORAGE_DIR / clean_name).resolve()
    
    # Safety: Verify that customer_dir is strictly inside INVOICE_STORAGE_DIR
    if not customer_dir.is_relative_to(INVOICE_STORAGE_DIR):
        raise ValueError("Invalid customer folder path: directory traversal attempt blocked")
        
    customer_dir.mkdir(parents=True, exist_ok=True)
    return customer_dir

def load_customer_history(customer_dir: Path):
    """
    Scan ONLY the selected customer's folder for previous invoice files.
    Extract order dates, order numbers, and order totals.
    """
    previous_orders = []
    if not customer_dir.exists() or not customer_dir.is_dir():
        return previous_orders
        
    xlsx_files = sorted(customer_dir.glob("*.xlsx"), key=lambda p: p.stat().st_mtime)
    
    for file_path in xlsx_files:
        wb = None
        try:
            wb = load_workbook(file_path, data_only=True)
            ws = wb.active
            
            found_order_totals = False
            for r_num in range(1, ws.max_row + 1):
                c_val = ws.cell(row=r_num, column=2).value
                if isinstance(c_val, str) and "Order Total (" in c_val:
                    dt_str = c_val.replace("Order Total (", "").replace("):", "").strip()
                    amt_cell = ws.cell(row=r_num, column=4)
                    if isinstance(amt_cell.value, (int, float)):
                        found_order_totals = True
                        previous_orders.append({
                            "order_number": len(previous_orders) + 1,
                            "date": dt_str,
                            "total": float(amt_cell.value),
                            "source_file": file_path.name
                        })
            
            if not found_order_totals:
                # Standalone invoice
                date_val = None
                cell_a2 = str(ws['A2'].value or '')
                cell_d5 = str(ws['D5'].value or '') if 'D5' in ws else ''
                
                if "Date:" in cell_d5:
                    date_val = cell_d5.replace("📅 Date:", "").replace("Date:", "").strip()
                elif "Date:" in cell_a2:
                    date_val = cell_a2.replace("📅 Date:", "").replace("Date:", "").strip()
                elif "Started:" in cell_a2:
                    date_val = cell_a2.replace("📅 Started:", "").replace("Started:", "").strip()
                else:
                    date_val = datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%d/%m/%Y')
                    
                total_val = None
                for r_num in range(1, ws.max_row + 1):
                    val_b = str(ws.cell(row=r_num, column=2).value or '')
                    val_d = ws.cell(row=r_num, column=4).value
                    if "TOTAL" in val_b.upper() and isinstance(val_d, (int, float)):
                        total_val = float(val_d)
                        break
                        
                if total_val is not None and total_val > 0:
                    previous_orders.append({
                        "order_number": len(previous_orders) + 1,
                        "date": date_val or datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%d/%m/%Y'),
                        "total": total_val,
                        "source_file": file_path.name
                    })
                    
        except Exception as err:
            print(f"Warning: Could not read history from {file_path.name}: {err}")
            continue
        finally:
            if wb:
                try:
                    wb.close()
                except Exception:
                    pass
            
    return previous_orders

def build_invoice_workbook(customer, products, invoice_number, current_date, invoice_type='current', previous_orders=None, extra_charges_desc='', extra_charges_amount=0.0):
    """Build a professional Excel workbook representing this invoice."""
    if previous_orders is None:
        previous_orders = []
        
    wb = Workbook()
    ws = wb.active
    ws.title = "Invoice"
    
    # Styling
    title_font = Font(name='Arial', size=18, bold=True, color='1E1B4B')
    subtitle_font = Font(name='Arial', size=10, bold=True, color='4F46E5')
    header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
    date_font = Font(name='Arial', size=10, color='475569')
    normal_font = Font(name='Arial', size=10)
    bold_font = Font(name='Arial', size=10, bold=True)
    total_font = Font(name='Arial', size=11, bold=True, color='1E1B4B')
    grand_total_font = Font(name='Arial', size=14, bold=True, color='FFFFFF')
    
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'), right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'), bottom=Side(style='thin', color='CBD5E1')
    )
    thick_border = Border(
        left=Side(style='medium', color='1E1B4B'), right=Side(style='medium', color='1E1B4B'),
        top=Side(style='medium', color='1E1B4B'), bottom=Side(style='medium', color='1E1B4B')
    )
    header_fill = PatternFill(start_color="1E1B4B", end_color="1E1B4B", fill_type="solid")
    history_header_fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
    grand_total_fill = PatternFill(start_color="1E1B4B", end_color="1E1B4B", fill_type="solid")
    
    # Company Header
    ws['A1'] = "SRI LAXMI GAYATRI TRADERS"
    ws['A1'].font = title_font
    ws['A2'] = "WHOLESALE DISTRIBUTORS & GENERAL MERCHANTS"
    ws['A2'].font = subtitle_font
    
    # Invoice Meta
    ws['A4'] = "TAX INVOICE"
    ws['A4'].font = Font(name='Arial', size=14, bold=True, color='1E1B4B')
    ws['D4'] = f"Invoice No: {invoice_number}"
    ws['D4'].font = bold_font
    ws['D4'].alignment = Alignment(horizontal='right')
    
    ws['D5'] = f"📅 Date: {current_date}"
    ws['D5'].font = date_font
    ws['D5'].alignment = Alignment(horizontal='right')
    
    ws['D6'] = f"Bill Type: {'All Bills (With History)' if invoice_type == 'all' else 'Current Bill Only'}"
    ws['D6'].font = bold_font
    ws['D6'].alignment = Alignment(horizontal='right')
    
    # Customer Details
    ws['A6'] = "BILL TO / BUYER DETAILS:"
    ws['A6'].font = bold_font
    ws['A7'] = f"Shop Name: {customer['shopName']}"
    ws['A7'].font = Font(name='Arial', size=11, bold=True, color='0F172A')
    ws['A8'] = f"Area: {customer['area']}"
    ws['A8'].font = normal_font
    
    row = 10
    prev_sum = 0
    
    # If All Bills and previous orders exist, render Previous Orders table
    if invoice_type == 'all' and previous_orders:
        ws.cell(row=row, column=1, value="📜 PREVIOUS ORDERS HISTORY (ACCOUNT STATEMENT)").font = Font(name='Arial', size=11, bold=True, color='334155')
        row += 1
        
        hist_headers = ["Order #", "Order Date", "Description / Reference", "Amount (₹)"]
        for c_idx, h_text in enumerate(hist_headers, 1):
            c = ws.cell(row=row, column=c_idx, value=h_text)
            c.font = Font(name='Arial', size=10, bold=True, color='FFFFFF')
            c.fill = history_header_fill
            c.alignment = Alignment(horizontal='center' if c_idx in [1, 2] else ('right' if c_idx == 4 else 'left'))
            c.border = thin_border
        row += 1
        
        for ord_info in previous_orders:
            ws.cell(row=row, column=1, value=f"#{ord_info.get('order_number', '')}").alignment = Alignment(horizontal='center')
            ws.cell(row=row, column=2, value=str(ord_info.get('date', ''))).alignment = Alignment(horizontal='center')
            ws.cell(row=row, column=3, value="Wholesale Order Billing")
            amt_val = float(ord_info.get('total', 0))
            prev_sum += amt_val
            c_amt = ws.cell(row=row, column=4, value=amt_val)
            c_amt.alignment = Alignment(horizontal='right')
            c_amt.number_format = '"₹"#,##0.00'
            for c_idx in range(1, 5):
                ws.cell(row=row, column=c_idx).border = thin_border
                ws.cell(row=row, column=c_idx).font = normal_font
            row += 1
            
        ws.cell(row=row, column=3, value=f"Previous Orders Total ({len(previous_orders)} orders):").font = bold_font
        ws.cell(row=row, column=3).alignment = Alignment(horizontal='right')
        c_prev_tot = ws.cell(row=row, column=4, value=prev_sum)
        c_prev_tot.font = bold_font
        c_prev_tot.alignment = Alignment(horizontal='right')
        c_prev_tot.number_format = '"₹"#,##0.00'
        c_prev_tot.border = thick_border
        row += 2
        
    # Current Order Items Table
    section_label = "🛍️ CURRENT ORDER (TODAY'S INVOICE)" if (invoice_type == 'all' and previous_orders) else "PARTICULARS / GOODS"
    ws.cell(row=row, column=1, value=section_label).font = Font(name='Arial', size=11, bold=True, color='1E1B4B')
    row += 1
    
    headers = ["Description of Goods", "Qty", "Unit Price", "Total Price"]
    for c_idx, h_text in enumerate(headers, 1):
        c = ws.cell(row=row, column=c_idx, value=h_text)
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal='center' if c_idx == 2 else ('right' if c_idx in [3, 4] else 'left'))
        c.border = thin_border
    row += 1
    
    product_subtotal = 0.0
    for p in products:
        p_name = str(p.get('name') or p.get('productName') or '')
        p_qty = int(p.get('quantity', 0))
        p_price = float(p.get('price') if p.get('price') is not None else p.get('unitPrice', 0))
        p_total = float(p.get('total') if p.get('total') is not None else (p_qty * p_price))
        product_subtotal += p_total
        ws.cell(row=row, column=1, value=p_name)
        c_qty = ws.cell(row=row, column=2, value=p_qty)
        c_qty.alignment = Alignment(horizontal='center')
        c_rate = ws.cell(row=row, column=3, value=p_price)
        c_rate.alignment = Alignment(horizontal='right')
        c_rate.number_format = '"₹"#,##0.00'
        c_amt = ws.cell(row=row, column=4, value=p_total)
        c_amt.alignment = Alignment(horizontal='right')
        c_amt.number_format = '"₹"#,##0.00'
        for c_idx in range(1, 5):
            ws.cell(row=row, column=c_idx).border = thin_border
            ws.cell(row=row, column=c_idx).font = normal_font
        row += 1
        
    clean_extra_amt = float(extra_charges_amount or 0.0)
    clean_extra_desc = str(extra_charges_desc or '').strip()
    if not clean_extra_desc:
        clean_extra_desc = "Extra Charges"

    # If extra charges exist, write Subtotal and Extra Charges rows
    if clean_extra_amt > 0:
        ws.cell(row=row, column=2, value="Product Subtotal:").font = bold_font
        ws.cell(row=row, column=2).alignment = Alignment(horizontal='right')
        c_sub = ws.cell(row=row, column=4, value=product_subtotal)
        c_sub.font = bold_font
        c_sub.alignment = Alignment(horizontal='right')
        c_sub.number_format = '"₹"#,##0.00'
        c_sub.border = thin_border
        row += 1

        ws.cell(row=row, column=2, value=f"{clean_extra_desc}:").font = bold_font
        ws.cell(row=row, column=2).alignment = Alignment(horizontal='right')
        c_ext = ws.cell(row=row, column=4, value=clean_extra_amt)
        c_ext.font = bold_font
        c_ext.alignment = Alignment(horizontal='right')
        c_ext.number_format = '"₹"#,##0.00'
        c_ext.border = thin_border
        row += 1

    current_order_total = product_subtotal + clean_extra_amt

    # Current Order Total Row
    order_total_label = "Current Order Total:" if (invoice_type == 'all' and previous_orders) else "Grand Total:"
    ws.cell(row=row, column=2, value=order_total_label).font = bold_font
    ws.cell(row=row, column=2).alignment = Alignment(horizontal='right')
    c_tot = ws.cell(row=row, column=4, value=current_order_total)
    c_tot.font = total_font
    c_tot.alignment = Alignment(horizontal='right')
    c_tot.number_format = '"₹"#,##0.00'
    c_tot.border = thick_border
    row += 1
    
    # Grand Total Row
    if invoice_type == 'all' and previous_orders:
        row += 1
        grand_total = prev_sum + current_order_total
        gt_lbl = ws.cell(row=row, column=2, value=f"CUMULATIVE GRAND TOTAL ({len(previous_orders) + 1} orders):")
        gt_lbl.font = Font(name='Arial', size=12, bold=True, color='FFFFFF')
        gt_lbl.alignment = Alignment(horizontal='right')
        gt_lbl.fill = grand_total_fill
        
        gt_val = ws.cell(row=row, column=4, value=grand_total)
        gt_val.font = grand_total_font
        gt_val.alignment = Alignment(horizontal='right')
        gt_val.fill = grand_total_fill
        gt_val.number_format = '"₹"#,##0.00'
        gt_val.border = thick_border
    else:
        grand_total = current_order_total
        
    # Column dimensions
    ws.column_dimensions['A'].width = 38
    ws.column_dimensions['B'].width = 16
    ws.column_dimensions['C'].width = 18
    ws.column_dimensions['D'].width = 20
    
    return wb, current_order_total, grand_total

def create_excel_invoice(customer, products, invoice_number, invoice_type='current', invoice_date=None, is_edit=False, extra_charges_desc='', extra_charges_amount=0.0):
    """
    Create customer-wise invoice and store inside customer-specific folder in Invoice Storage.
    Supports both 'current' and 'all' (with history).
    """
    shop_name = customer.get('shopName', '').strip()
    customer_dir = get_or_create_customer_dir(shop_name)
    
    if invoice_date:
        if isinstance(invoice_date, datetime):
            current_date = invoice_date.strftime('%d/%m/%Y')
        else:
            try:
                parsed_dt = datetime.fromisoformat(str(invoice_date).replace('Z', ''))
                current_date = parsed_dt.strftime('%d/%m/%Y')
            except Exception:
                current_date = str(invoice_date)
    else:
        current_date = datetime.now().strftime('%d/%m/%Y')
    
    # If 'all', load history strictly from database (PostgreSQL/SQLite), with fallback to folder scan
    if invoice_type == 'all':
        previous_orders = learning_db.get_customer_invoice_history(shop_name, exclude_invoice_number=invoice_number if is_edit else None)
        if not previous_orders:
            previous_orders = load_customer_history(customer_dir)
            if is_edit:
                # Filter out this existing invoice from previous orders to prevent double-counting
                previous_orders = [o for o in previous_orders if str(o.get('order_number', '')).strip() != str(invoice_number).strip()]
    else:
        previous_orders = []

        
    # Generate unique filename using existing invoice number and timestamp
    safe_inv = re.sub(r'[\\/*?:"<>|\s]', "", str(invoice_number))
    if not safe_inv:
        safe_inv = generate_invoice_number()
    filename = f"{safe_inv}.xlsx"
    target_path = customer_dir / filename
    
    # Only append timestamp suffix if creating new and conflict exists, not when editing this invoice
    if not is_edit and target_path.exists():
        timestamp_suffix = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{safe_inv}_{timestamp_suffix}.xlsx"
        target_path = customer_dir / filename
        
    # Build Excel workbook
    wb, current_total, grand_total = build_invoice_workbook(
        customer, products, invoice_number, current_date, invoice_type, previous_orders,
        extra_charges_desc=extra_charges_desc, extra_charges_amount=extra_charges_amount
    )
    
    # Save into customer's dedicated folder
    wb.save(str(target_path))
    print(f"📁 Saved invoice to customer folder: {target_path}")
    
    # Also copy to tempdir for web download route compatibility
    temp_path = Path(tempfile.gettempdir()) / filename
    wb.save(str(temp_path))
    wb.close()
    
    order_count = (len(previous_orders) + 1) if (invoice_type == 'all' and previous_orders) else 1
    first_date = previous_orders[0]['date'] if (invoice_type == 'all' and previous_orders) else current_date
    
    clean_extra_amt = float(extra_charges_amount or 0.0)
    history_data = {
        'previous_orders': previous_orders if invoice_type == 'all' else [],
        'product_subtotal': current_total - clean_extra_amt,
        'extra_charges_desc': extra_charges_desc or '',
        'extra_charges_amount': clean_extra_amt,
        'current_order_total': current_total,
        'grand_total': grand_total,
        'order_count': order_count,
        'first_order_date': first_date,
        'latest_order_date': current_date
    }
    
    return filename, history_data

if __name__ == '__main__':
    is_desktop = os.environ.get('DESKTOP_MODE') == '1'
    port = int(os.environ.get('PORT', 5000))
    host = '127.0.0.1' if is_desktop else '0.0.0.0'
    debug = False if is_desktop else True
    use_reloader = False if is_desktop else True
    
    mode_str = "Desktop App Mode" if is_desktop else "Web Server Mode"
    print(f"🚀 Starting Invoice Generator ({mode_str})...")
    print(f"📄 Listening on: http://{host}:{port}")
    if not is_desktop:
        print("🛑 Press Ctrl+C to stop the server")
    
    app.run(debug=debug, host=host, port=port, use_reloader=use_reloader)