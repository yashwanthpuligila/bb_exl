import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date
import os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter


class InvoiceGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Professional Invoice Generator")
        self.root.geometry("900x700")
        self.root.configure(bg='#f0f0f0')
        
        # Invoice data storage
        self.items = []
        self.next_invoice_number = self.get_next_invoice_number()
        
        self.create_widgets()
        
    def get_next_invoice_number(self):
        """Get the next invoice number by checking existing invoices"""
        # Simple implementation - you can enhance this to read from a file
        return datetime.now().strftime("%Y%m%d") + "001"
        
    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Professional Invoice Generator", 
                               font=('Arial', 18, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Create notebook for sections
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill='both', expand=True)
        
        # Company Information Tab
        self.create_company_tab(notebook)
        
        # Customer Information Tab
        self.create_customer_tab(notebook)
        
        # Invoice Items Tab
        self.create_items_tab(notebook)
        
        # Generate Invoice Tab
        self.create_generate_tab(notebook)
        
    def create_company_tab(self, parent):
        company_frame = ttk.Frame(parent)
        parent.add(company_frame, text="Company Info")
        
        # Company details form
        form_frame = ttk.LabelFrame(company_frame, text="Your Company Details", padding=20)
        form_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Company Name
        ttk.Label(form_frame, text="Company Name:").grid(row=0, column=0, sticky='w', pady=5)
        self.company_name = ttk.Entry(form_frame, width=50, font=('Arial', 10))
        self.company_name.insert(0, "Your Company")
        self.company_name.grid(row=0, column=1, padx=(10, 0), pady=5, sticky='ew')
        
        # Address
        ttk.Label(form_frame, text="Address Line 1:").grid(row=1, column=0, sticky='w', pady=5)
        self.company_address1 = ttk.Entry(form_frame, width=50)
        self.company_address1.insert(0, "123 Your Street")
        self.company_address1.grid(row=1, column=1, padx=(10, 0), pady=5, sticky='ew')
        
        ttk.Label(form_frame, text="Address Line 2:").grid(row=2, column=0, sticky='w', pady=5)
        self.company_address2 = ttk.Entry(form_frame, width=50)
        self.company_address2.insert(0, "Your City, ST 12345")
        self.company_address2.grid(row=2, column=1, padx=(10, 0), pady=5, sticky='ew')
        
        # Phone
        ttk.Label(form_frame, text="Phone:").grid(row=3, column=0, sticky='w', pady=5)
        self.company_phone = ttk.Entry(form_frame, width=50)
        self.company_phone.insert(0, "(123) 456-7890")
        self.company_phone.grid(row=3, column=1, padx=(10, 0), pady=5, sticky='ew')
        
        # Configure grid
        form_frame.grid_columnconfigure(1, weight=1)
        
    def create_customer_tab(self, parent):
        customer_frame = ttk.Frame(parent)
        parent.add(customer_frame, text="Customer Info")
        
        form_frame = ttk.LabelFrame(customer_frame, text="Customer Details", padding=20)
        form_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Shop Name
        ttk.Label(form_frame, text="Shop Name:").grid(row=0, column=0, sticky='w', pady=5)
        self.shop_name = ttk.Entry(form_frame, width=50, font=('Arial', 10))
        self.shop_name.grid(row=0, column=1, padx=(10, 0), pady=5, sticky='ew')
        
        # Customer Name
        ttk.Label(form_frame, text="Customer Name:").grid(row=1, column=0, sticky='w', pady=5)
        self.customer_name = ttk.Entry(form_frame, width=50)
        self.customer_name.grid(row=1, column=1, padx=(10, 0), pady=5, sticky='ew')
        
        # Area
        ttk.Label(form_frame, text="Area:").grid(row=2, column=0, sticky='w', pady=5)
        self.customer_area = ttk.Entry(form_frame, width=50)
        self.customer_area.grid(row=2, column=1, padx=(10, 0), pady=5, sticky='ew')
        
        # Contact
        ttk.Label(form_frame, text="Contact:").grid(row=3, column=0, sticky='w', pady=5)
        self.customer_contact = ttk.Entry(form_frame, width=50)
        self.customer_contact.grid(row=3, column=1, padx=(10, 0), pady=5, sticky='ew')
        
        # Project/Reference
        ttk.Label(form_frame, text="Project/Reference:").grid(row=4, column=0, sticky='w', pady=5)
        self.project_name = ttk.Entry(form_frame, width=50)
        self.project_name.grid(row=4, column=1, padx=(10, 0), pady=5, sticky='ew')
        
        form_frame.grid_columnconfigure(1, weight=1)
        
    def create_items_tab(self, parent):
        items_frame = ttk.Frame(parent)
        parent.add(items_frame, text="Invoice Items")
        
        # Add item form
        add_form = ttk.LabelFrame(items_frame, text="Add New Item", padding=15)
        add_form.pack(fill='x', padx=20, pady=(20, 10))
        
        # Product description
        ttk.Label(add_form, text="Product Description:").grid(row=0, column=0, sticky='w', pady=5)
        self.item_description = ttk.Entry(add_form, width=40)
        self.item_description.grid(row=0, column=1, padx=(10, 20), pady=5, sticky='ew')
        
        # Quantity
        ttk.Label(add_form, text="Quantity:").grid(row=0, column=2, sticky='w', pady=5)
        self.item_quantity = ttk.Entry(add_form, width=15)
        self.item_quantity.grid(row=0, column=3, padx=(10, 20), pady=5)
        
        # Unit Price
        ttk.Label(add_form, text="Unit Price:").grid(row=1, column=0, sticky='w', pady=5)
        self.item_price = ttk.Entry(add_form, width=20)
        self.item_price.grid(row=1, column=1, padx=(10, 20), pady=5, sticky='w')
        
        # Add button
        add_button = ttk.Button(add_form, text="Add Item", command=self.add_item)
        add_button.grid(row=1, column=2, columnspan=2, padx=10, pady=5, sticky='ew')
        
        add_form.grid_columnconfigure(1, weight=1)
        
        # Items list
        list_frame = ttk.LabelFrame(items_frame, text="Invoice Items", padding=15)
        list_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        # Items treeview
        columns = ('Description', 'Qty', 'Unit Price', 'Total Price')
        self.items_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.items_tree.heading(col, text=col)
            if col == 'Description':
                self.items_tree.column(col, width=300)
            elif col == 'Qty':
                self.items_tree.column(col, width=80, anchor='center')
            else:
                self.items_tree.column(col, width=120, anchor='e')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.items_tree.yview)
        self.items_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.items_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Control buttons
        button_frame = ttk.Frame(list_frame)
        button_frame.pack(fill='x', pady=(10, 0))
        
        remove_button = ttk.Button(button_frame, text="Remove Selected", command=self.remove_item)
        remove_button.pack(side='left', padx=(0, 10))
        
        clear_button = ttk.Button(button_frame, text="Clear All", command=self.clear_items)
        clear_button.pack(side='left')
        
        # Totals frame
        totals_frame = ttk.LabelFrame(items_frame, text="Invoice Totals", padding=15)
        totals_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        # Subtotal
        ttk.Label(totals_frame, text="Subtotal:").grid(row=0, column=0, sticky='w', pady=2)
        self.subtotal_label = ttk.Label(totals_frame, text="$0.00", font=('Arial', 10, 'bold'))
        self.subtotal_label.grid(row=0, column=1, sticky='e', pady=2)
        
        # Adjustment
        ttk.Label(totals_frame, text="Adjustment:").grid(row=1, column=0, sticky='w', pady=2)
        self.adjustment_entry = ttk.Entry(totals_frame, width=15)
        self.adjustment_entry.insert(0, "0.00")
        self.adjustment_entry.bind('<KeyRelease>', self.calculate_totals)
        self.adjustment_entry.grid(row=1, column=1, sticky='e', pady=2)
        
        # Total
        ttk.Label(totals_frame, text="Total Amount:", font=('Arial', 12, 'bold')).grid(row=2, column=0, sticky='w', pady=5)
        self.total_label = ttk.Label(totals_frame, text="$0.00", font=('Arial', 14, 'bold'), foreground='red')
        self.total_label.grid(row=2, column=1, sticky='e', pady=5)
        
        totals_frame.grid_columnconfigure(1, weight=1)
        
    def create_generate_tab(self, parent):
        generate_frame = ttk.Frame(parent)
        parent.add(generate_frame, text="Generate Invoice")
        
        # Invoice details
        details_frame = ttk.LabelFrame(generate_frame, text="Invoice Details", padding=20)
        details_frame.pack(fill='x', padx=20, pady=20)
        
        # Invoice number
        ttk.Label(details_frame, text="Invoice Number:").grid(row=0, column=0, sticky='w', pady=5)
        self.invoice_number = ttk.Entry(details_frame, width=20)
        self.invoice_number.insert(0, self.next_invoice_number)
        self.invoice_number.grid(row=0, column=1, padx=(10, 0), pady=5, sticky='w')
        
        # Due date
        ttk.Label(details_frame, text="Due Date:").grid(row=0, column=2, sticky='w', pady=5, padx=(30, 0))
        self.due_date = ttk.Entry(details_frame, width=20)
        self.due_date.insert(0, datetime.now().strftime("%m/%d/%Y"))
        self.due_date.grid(row=0, column=3, padx=(10, 0), pady=5, sticky='w')
        
        # Notes
        ttk.Label(details_frame, text="Notes:").grid(row=1, column=0, sticky='nw', pady=5)
        self.notes_text = tk.Text(details_frame, width=60, height=4)
        self.notes_text.grid(row=1, column=1, columnspan=3, padx=(10, 0), pady=5, sticky='ew')
        
        details_frame.grid_columnconfigure(1, weight=1)
        
        # Preview and Generate buttons
        button_frame = ttk.Frame(generate_frame)
        button_frame.pack(fill='x', padx=20, pady=20)
        
        preview_button = ttk.Button(button_frame, text="Preview Invoice", 
                                   command=self.preview_invoice, style='Accent.TButton')
        preview_button.pack(side='left', padx=(0, 20))
        
        generate_button = ttk.Button(button_frame, text="Generate Excel Invoice", 
                                    command=self.generate_excel_invoice, style='Accent.TButton')
        generate_button.pack(side='left')
        
        # Status label
        self.status_label = ttk.Label(generate_frame, text="Ready to generate invoice...", 
                                     foreground='green')
        self.status_label.pack(pady=10)
        
    def add_item(self):
        try:
            description = self.item_description.get().strip()
            quantity_str = self.item_quantity.get().strip()
            price_str = self.item_price.get().strip()
            
            if not description:
                raise ValueError("Product description is required")
            if not quantity_str:
                raise ValueError("Quantity is required")
            if not price_str:
                raise ValueError("Unit price is required")
                
            quantity = int(quantity_str)
            price = float(price_str)
            
            if quantity <= 0:
                raise ValueError("Quantity must be greater than 0")
            if price < 0:
                raise ValueError("Price cannot be negative")
                
            total = quantity * price
            
            # Add to items list
            item = {
                'description': description,
                'quantity': quantity,
                'price': price,
                'total': total
            }
            self.items.append(item)
            
            # Add to treeview
            self.items_tree.insert('', 'end', values=(
                description,
                quantity,
                f"${price:.2f}",
                f"${total:.2f}"
            ))
            
            # Clear form
            self.item_description.delete(0, tk.END)
            self.item_quantity.delete(0, tk.END)
            self.item_price.delete(0, tk.END)
            
            # Update totals
            self.calculate_totals()
            
            self.status_label.config(text=f"Item added: {description}", foreground='green')
            
        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
            
    def remove_item(self):
        selected = self.items_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select an item to remove")
            return
            
        # Get index and remove from both list and treeview
        for item in selected:
            index = self.items_tree.index(item)
            del self.items[index]
            self.items_tree.delete(item)
            
        self.calculate_totals()
        self.status_label.config(text="Item removed", foreground='blue')
        
    def clear_items(self):
        if messagebox.askyesno("Confirm", "Clear all items?"):
            self.items.clear()
            for item in self.items_tree.get_children():
                self.items_tree.delete(item)
            self.calculate_totals()
            self.status_label.config(text="All items cleared", foreground='blue')
            
    def calculate_totals(self, event=None):
        subtotal = sum(item['total'] for item in self.items)
        
        try:
            adjustment = float(self.adjustment_entry.get() or "0")
        except ValueError:
            adjustment = 0.0
            
        total = subtotal + adjustment
        
        self.subtotal_label.config(text=f"${subtotal:.2f}")
        self.total_label.config(text=f"${total:.2f}")
        
    def preview_invoice(self):
        if not self.items:
            messagebox.showwarning("No Items", "Please add at least one item to the invoice")
            return
            
        # Create preview window
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Invoice Preview")
        preview_window.geometry("800x900")
        
        # Create canvas for scrolling
        canvas = tk.Canvas(preview_window)
        scrollbar = ttk.Scrollbar(preview_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Generate preview content
        self.create_invoice_preview(scrollable_frame)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_invoice_preview(self, parent):
        # Company header
        company_frame = ttk.Frame(parent)
        company_frame.pack(fill='x', padx=20, pady=20)
        
        company_label = ttk.Label(company_frame, text=self.company_name.get(), 
                                 font=('Arial', 20, 'bold'), foreground='blue')
        company_label.pack()
        
        address_label = ttk.Label(company_frame, text=self.company_address1.get())
        address_label.pack()
        
        address2_label = ttk.Label(company_frame, text=self.company_address2.get())
        address2_label.pack()
        
        phone_label = ttk.Label(company_frame, text=self.company_phone.get())
        phone_label.pack()
        
        # Invoice title
        invoice_title = ttk.Label(parent, text="Invoice", font=('Arial', 24, 'bold'))
        invoice_title.pack(pady=20)
        
        date_label = ttk.Label(parent, text=f"Submitted on {datetime.now().strftime('%m/%d/%Y')}", 
                              font=('Arial', 10), foreground='red')
        date_label.pack()
        
        # Customer and invoice details
        details_frame = ttk.Frame(parent)
        details_frame.pack(fill='x', padx=20, pady=20)
        
        # Left column - customer info
        left_frame = ttk.Frame(details_frame)
        left_frame.pack(side='left', fill='both', expand=True)
        
        ttk.Label(left_frame, text="Invoice for", font=('Arial', 10, 'bold')).pack(anchor='w')
        ttk.Label(left_frame, text=self.shop_name.get(), font=('Arial', 10, 'bold')).pack(anchor='w')
        ttk.Label(left_frame, text=self.customer_name.get()).pack(anchor='w')
        ttk.Label(left_frame, text=self.customer_area.get()).pack(anchor='w')
        
        # Right column - invoice details  
        right_frame = ttk.Frame(details_frame)
        right_frame.pack(side='right', fill='both', expand=True)
        
        ttk.Label(right_frame, text=f"Invoice # {self.invoice_number.get()}", 
                 font=('Arial', 10, 'bold')).pack(anchor='e')
        ttk.Label(right_frame, text=f"Due date: {self.due_date.get()}").pack(anchor='e')
        
        if self.project_name.get():
            ttk.Label(right_frame, text=f"Project: {self.project_name.get()}").pack(anchor='e')
        
        # Items table (simplified preview)
        items_frame = ttk.LabelFrame(parent, text="Items", padding=10)
        items_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Headers
        header_frame = ttk.Frame(items_frame)
        header_frame.pack(fill='x')
        
        ttk.Label(header_frame, text="Description", font=('Arial', 10, 'bold')).pack(side='left')
        ttk.Label(header_frame, text="Qty", font=('Arial', 10, 'bold')).pack(side='right', padx=(0, 100))
        ttk.Label(header_frame, text="Unit Price", font=('Arial', 10, 'bold')).pack(side='right', padx=(0, 50))
        ttk.Label(header_frame, text="Total", font=('Arial', 10, 'bold')).pack(side='right')
        
        # Items
        for item in self.items:
            item_frame = ttk.Frame(items_frame)
            item_frame.pack(fill='x', pady=2)
            
            ttk.Label(item_frame, text=item['description']).pack(side='left')
            ttk.Label(item_frame, text=f"${item['total']:.2f}").pack(side='right')
            ttk.Label(item_frame, text=f"${item['price']:.2f}").pack(side='right', padx=(0, 50))
            ttk.Label(item_frame, text=str(item['quantity'])).pack(side='right', padx=(0, 100))
        
        # Totals
        totals_frame = ttk.Frame(parent)
        totals_frame.pack(fill='x', padx=20, pady=20)
        
        subtotal = sum(item['total'] for item in self.items)
        adjustment = float(self.adjustment_entry.get() or "0")
        total = subtotal + adjustment
        
        ttk.Label(totals_frame, text=f"Subtotal: ${subtotal:.2f}").pack(anchor='e')
        if adjustment != 0:
            ttk.Label(totals_frame, text=f"Adjustments: ${adjustment:.2f}").pack(anchor='e')
        ttk.Label(totals_frame, text=f"${total:.2f}", 
                 font=('Arial', 16, 'bold'), foreground='red').pack(anchor='e')
        
    def generate_excel_invoice(self):
        if not self.items:
            messagebox.showwarning("No Items", "Please add at least one item to the invoice")
            return
            
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="Save Invoice",
                initialname=f"Invoice_{self.invoice_number.get()}.xlsx"
            )
            
            if not filename:
                return
                
            self.create_excel_invoice(filename)
            self.status_label.config(text=f"Invoice saved: {filename}", foreground='green')
            messagebox.showinfo("Success", f"Invoice generated successfully!\n\nSaved as: {filename}")
            
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", foreground='red')
            messagebox.showerror("Error", f"Failed to generate invoice: {str(e)}")
            
    def create_excel_invoice(self, filename):
        wb = Workbook()
        ws = wb.active
        ws.title = "Invoice"
        
        # Styling
        header_font = Font(name='Arial', size=14, bold=True, color='4472C4')
        title_font = Font(name='Arial', size=24, bold=True, color='4472C4')
        bold_font = Font(name='Arial', size=10, bold=True)
        normal_font = Font(name='Arial', size=10)
        total_font = Font(name='Arial', size=14, bold=True, color='FF0000')
        
        # Borders
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Header fill
        header_fill = PatternFill(start_color='E7E6E6', end_color='E7E6E6', fill_type='solid')
        
        # Company information (rows 1-4)
        ws['A1'] = self.company_name.get()
        ws['A1'].font = header_font
        ws['A2'] = self.company_address1.get()
        ws['A3'] = self.company_address2.get()
        ws['A4'] = self.company_phone.get()
        
        # Invoice title (row 8)
        ws['A8'] = "Invoice"
        ws['A8'].font = title_font
        
        # Submission date (row 9)
        ws['A9'] = f"Submitted on {datetime.now().strftime('%m/%d/%Y')}"
        ws['A9'].font = Font(name='Arial', size=10, color='FF0000')
        
        # Customer information (starting row 11)
        ws['A11'] = "Invoice for"
        ws['A11'].font = bold_font
        ws['A12'] = self.shop_name.get()
        ws['A12'].font = bold_font
        ws['A13'] = self.customer_name.get()
        ws['A14'] = self.customer_area.get()
        
        # Invoice details (right side)
        ws['E11'] = "Payable to"
        ws['E11'].font = bold_font
        ws['E12'] = self.customer_name.get()
        
        ws['F11'] = f"Invoice # {self.invoice_number.get()}"
        ws['F11'].font = bold_font
        
        ws['E14'] = "Project"
        ws['E14'].font = bold_font
        ws['E15'] = self.project_name.get()
        
        ws['F14'] = "Due date"
        ws['F14'].font = bold_font
        ws['F15'] = self.due_date.get()
        
        # Items header (row 18)
        headers = ["Description", "Qty", "Unit price", "Total price"]
        for i, header in enumerate(headers, 1):
            cell = ws.cell(row=18, column=i)
            cell.value = header
            cell.font = bold_font
            cell.fill = header_fill
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center')
        
        # Items data
        row = 19
        subtotal = 0
        for item in self.items:
            ws.cell(row=row, column=1, value=item['description']).font = normal_font
            ws.cell(row=row, column=2, value=item['quantity']).font = normal_font
            ws.cell(row=row, column=2).alignment = Alignment(horizontal='center')
            ws.cell(row=row, column=3, value=item['price']).font = normal_font
            ws.cell(row=row, column=4, value=item['total']).font = normal_font
            
            # Add borders
            for col in range(1, 5):
                ws.cell(row=row, column=col).border = thin_border
            
            subtotal += item['total']
            row += 1
        
        # Totals section
        adjustment = float(self.adjustment_entry.get() or "0")
        total = subtotal + adjustment
        
        # Subtotal
        ws.cell(row=row+1, column=3, value="Subtotal").font = bold_font
        ws.cell(row=row+1, column=3).alignment = Alignment(horizontal='right')
        ws.cell(row=row+1, column=4, value=subtotal).font = bold_font
        
        # Adjustments (if any)
        if adjustment != 0:
            ws.cell(row=row+2, column=3, value="Adjustments").font = bold_font
            ws.cell(row=row+2, column=3).alignment = Alignment(horizontal='right')
            ws.cell(row=row+2, column=4, value=adjustment).font = bold_font
            row += 1
        
        # Total
        ws.cell(row=row+2, column=4, value=total).font = total_font
        ws.cell(row=row+2, column=4).alignment = Alignment(horizontal='right')
        
        # Add border around total
        total_cell = ws.cell(row=row+2, column=4)
        total_cell.border = Border(
            left=Side(style='thick'),
            right=Side(style='thick'),
            top=Side(style='thick'),
            bottom=Side(style='thick')
        )
        
        # Format currency columns
        for row_num in range(19, 19 + len(self.items)):
            ws.cell(row=row_num, column=3).number_format = '"$"#,##0.00'
            ws.cell(row=row_num, column=4).number_format = '"$"#,##0.00'
        
        # Format total cells
        ws.cell(row=19+len(self.items)+1, column=4).number_format = '"$"#,##0.00'
        if adjustment != 0:
            ws.cell(row=19+len(self.items)+2, column=4).number_format = '"$"#,##0.00'
        ws.cell(row=19+len(self.items)+2+(1 if adjustment != 0 else 0), column=4).number_format = '"$"#,##0.00'
        
        # Adjust column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 10
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 15
        ws.column_dimensions['E'].width = 15
        ws.column_dimensions['F'].width = 15
        
        # Add notes if provided
        notes = self.notes_text.get("1.0", tk.END).strip()
        if notes:
            notes_row = 19 + len(self.items) + 5
            ws.cell(row=notes_row, column=1, value="Notes:").font = bold_font
            ws.cell(row=notes_row+1, column=1, value=notes).font = normal_font
        
        wb.save(filename)


def main():
    root = tk.Tk()
    
    # Set up modern styling
    style = ttk.Style()
    
    # Try to use a modern theme if available
    available_themes = style.theme_names()
    if 'winnative' in available_themes:
        style.theme_use('winnative')
    elif 'clam' in available_themes:
        style.theme_use('clam')
    
    app = InvoiceGenerator(root)
    root.mainloop()


if __name__ == "__main__":
    main()