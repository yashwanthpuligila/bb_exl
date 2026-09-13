from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import re
from pathlib import Path
from datetime import datetime
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
import tempfile
import json
import glob
from recommendation_engine import recommendation_engine
import learning_db

# Main Invoice Storage Directory at project root: e:\bb_exl\Invoice Storage
INVOICE_STORAGE_DIR = (Path(__file__).resolve().parent.parent / "Invoice Storage").resolve()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize recommendation engine on startup
@app.before_request
def initialize_recommendations():
    """Initialize ML recommendation engine and learning DB with historical data"""
    if not hasattr(app, 'recommendations_loaded'):
        print("🤖 Loading ML recommendation engine...")
        recommendation_engine.load_data_from_invoices('.')
        recommendation_engine.load_data_from_invoices('..')  # Check parent directory too
        if INVOICE_STORAGE_DIR.exists():
            recommendation_engine.load_data_from_invoices(str(INVOICE_STORAGE_DIR))
        
        # Initialize learning db from historical invoices
        try:
            dirs_to_check = ['.', '..']
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
    return send_file('index.html')

@app.route('/styles.css')
def styles():
    """Serve CSS file"""
    return send_file('styles.css', mimetype='text/css')

@app.route('/script.js')
def script():
    """Serve JavaScript file"""
    return send_file('script.js', mimetype='application/javascript')

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
        invoice_type = data.get('invoiceType', 'current')  # 'current' or 'all'
        
        # Validate customer data
        required_fields = ['shopName', 'area']
        for field in required_fields:
            if not customer.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        if not products:
            return jsonify({'error': 'No products provided'}), 400
        
        # Generate invoice number
        invoice_number = generate_invoice_number()
        
        # Create Excel file and get history data
        filename, history_data = create_excel_invoice(customer, products, invoice_number, invoice_type)
        
        # Immediately record customer and products in learning database
        try:
            learning_db.record_customer(
                customer.get('shopName', ''),
                customer.get('area', ''),
                invoice_number=invoice_number
            )
            for prod in products:
                learning_db.record_product(
                    prod.get('name', ''),
                    prod.get('price', 0.0),
                    invoice_number=invoice_number
                )
                learning_db.record_customer_purchase(
                    customer.get('shopName', ''),
                    prod.get('name', ''),
                    quantity=prod.get('quantity', 1.0),
                    price=prod.get('price', 0.0),
                    invoice_number=invoice_number
                )
        except Exception as learn_err:
            print(f"Error learning customer/product: {learn_err}")

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
    """Download generated Excel file safely"""
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

@app.route('/api/stats')
def get_stats():
    """Get overall system statistics"""
    try:
        total_customers = len(recommendation_engine.customer_products)
        total_products = len(recommendation_engine.product_popularity)
        total_orders = sum(recommendation_engine.product_popularity.values())
        
        return jsonify({
            'success': True,
            'stats': {
                'total_customers': total_customers,
                'total_products': total_products,
                'total_orders': total_orders
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generate_invoice_number():
    """Generate unique invoice number"""
    now = datetime.now()
    return f"INV-{now.strftime('%Y%m%d-%H%M%S')}"

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
            
    return previous_orders

def build_invoice_workbook(customer, products, invoice_number, current_date, invoice_type='current', previous_orders=None):
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
    
    current_order_total = 0
    for p in products:
        p_total = float(p.get('total', 0))
        current_order_total += p_total
        ws.cell(row=row, column=1, value=str(p.get('name', '')))
        c_qty = ws.cell(row=row, column=2, value=int(p.get('quantity', 0)))
        c_qty.alignment = Alignment(horizontal='center')
        c_rate = ws.cell(row=row, column=3, value=float(p.get('price', 0)))
        c_rate.alignment = Alignment(horizontal='right')
        c_rate.number_format = '"₹"#,##0.00'
        c_amt = ws.cell(row=row, column=4, value=p_total)
        c_amt.alignment = Alignment(horizontal='right')
        c_amt.number_format = '"₹"#,##0.00'
        for c_idx in range(1, 5):
            ws.cell(row=row, column=c_idx).border = thin_border
            ws.cell(row=row, column=c_idx).font = normal_font
        row += 1
        
    # Current Order Total Row
    ws.cell(row=row, column=2, value="Current Order Total:").font = bold_font
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

def create_excel_invoice(customer, products, invoice_number, invoice_type='current'):
    """
    Create customer-wise invoice and store inside customer-specific folder in Invoice Storage.
    Supports both 'current' and 'all' (with history).
    """
    shop_name = customer.get('shopName', '').strip()
    customer_dir = get_or_create_customer_dir(shop_name)
    current_date = datetime.now().strftime('%d/%m/%Y')
    
    # If 'all', load history strictly from this customer's folder
    if invoice_type == 'all':
        previous_orders = load_customer_history(customer_dir)
    else:
        previous_orders = []
        
    # Generate unique filename using existing invoice number and timestamp
    safe_inv = re.sub(r'[\\/*?:"<>|\s]', "", str(invoice_number))
    if not safe_inv:
        safe_inv = generate_invoice_number()
    filename = f"{safe_inv}.xlsx"
    target_path = customer_dir / filename
    
    # Ensure unique filename if conflict
    if target_path.exists():
        timestamp_suffix = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{safe_inv}_{timestamp_suffix}.xlsx"
        target_path = customer_dir / filename
        
    # Build Excel workbook
    wb, current_total, grand_total = build_invoice_workbook(
        customer, products, invoice_number, current_date, invoice_type, previous_orders
    )
    
    # Save into customer's dedicated folder
    wb.save(str(target_path))
    print(f"📁 Saved invoice to customer folder: {target_path}")
    
    # Also copy to tempdir for web download route compatibility
    temp_path = Path(tempfile.gettempdir()) / filename
    wb.save(str(temp_path))
    
    order_count = (len(previous_orders) + 1) if (invoice_type == 'all' and previous_orders) else 1
    first_date = previous_orders[0]['date'] if (invoice_type == 'all' and previous_orders) else current_date
    
    history_data = {
        'previous_orders': previous_orders if invoice_type == 'all' else [],
        'grand_total': grand_total,
        'order_count': order_count,
        'first_order_date': first_date,
        'latest_order_date': current_date
    }
    
    return filename, history_data

if __name__ == '__main__':
    print("🚀 Starting Invoice Generator Web Server...")
    print("📄 Open your browser and go to: http://localhost:5000")
    print("🛑 Press Ctrl+C to stop the server")
    
    app.run(debug=True, host='0.0.0.0', port=5000)