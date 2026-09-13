import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter


class CustomerInvoiceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Customer Invoice System")
        self.root.geometry("800x700")
        self.root.configure(bg='#f0f0f0')
        
        # Current customer data
        self.current_customer = {}
        self.customer_items = []
        
        # Setup styles
        self.setup_styles()
        
        # Create the main interface
        self.create_main_interface()
        
    def setup_styles(self):
        style = ttk.Style()
        
        # Configure button style
        style.configure('Large.TButton', 
                       font=('Arial', 11, 'bold'),
                       padding=(20, 10))
                       
        style.configure('Success.TButton',
                       font=('Arial', 10, 'bold'),
                       foreground='green')
        
    def create_main_interface(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, 
                               text="Customer Invoice System", 
                               font=('Arial', 18, 'bold'))
        title_label.pack(pady=(0, 30))
        
        # Step 1: Customer Information
        self.create_customer_section(main_frame)
        
        # Step 2: Products Section (initially hidden)
        self.create_products_section(main_frame)
        
        # Step 3: Generate Invoice Section (initially hidden)
        self.create_invoice_section(main_frame)
        
        # Status label
        self.status_label = ttk.Label(main_frame, 
                                     text="Enter customer details to start...", 
                                     font=('Arial', 10),
                                     foreground='blue')
        self.status_label.pack(pady=10)
        
    def create_customer_section(self, parent):
        # Customer Information Frame
        self.customer_frame = ttk.LabelFrame(parent, 
                                           text="Step 1: Customer Information", 
                                           padding=20)
        self.customer_frame.pack(fill='x', pady=(0, 20))
        
        # Shop Name
        ttk.Label(self.customer_frame, 
                 text="Shop Name:", 
                 font=('Arial', 10, 'bold')).grid(row=0, column=0, 
                                                 sticky='w', pady=8)
        self.shop_name_entry = ttk.Entry(self.customer_frame, 
                                        width=40, 
                                        font=('Arial', 11))
        self.shop_name_entry.grid(row=0, column=1, 
                                 padx=(15, 0), pady=8, sticky='ew')
        
        # Customer Name
        ttk.Label(self.customer_frame, 
                 text="Customer Name:", 
                 font=('Arial', 10, 'bold')).grid(row=1, column=0, 
                                                 sticky='w', pady=8)
        self.customer_name_entry = ttk.Entry(self.customer_frame, 
                                           width=40, 
                                           font=('Arial', 11))
        self.customer_name_entry.grid(row=1, column=1, 
                                     padx=(15, 0), pady=8, sticky='ew')
        
        # Area
        ttk.Label(self.customer_frame, 
                 text="Area:", 
                 font=('Arial', 10, 'bold')).grid(row=2, column=0, 
                                                 sticky='w', pady=8)
        self.area_entry = ttk.Entry(self.customer_frame, 
                                   width=40, 
                                   font=('Arial', 11))
        self.area_entry.grid(row=2, column=1, 
                            padx=(15, 0), pady=8, sticky='ew')
        
        # Contact (optional)
        ttk.Label(self.customer_frame, 
                 text="Contact:", 
                 font=('Arial', 10)).grid(row=3, column=0, 
                                         sticky='w', pady=8)
        self.contact_entry = ttk.Entry(self.customer_frame, 
                                      width=40, 
                                      font=('Arial', 11))
        self.contact_entry.grid(row=3, column=1, 
                               padx=(15, 0), pady=8, sticky='ew')
        
        # Confirm Customer Button
        self.confirm_customer_btn = ttk.Button(self.customer_frame, 
                                             text="Confirm Customer Details", 
                                             command=self.confirm_customer,
                                             style='Large.TButton')
        self.confirm_customer_btn.grid(row=4, column=0, columnspan=2, 
                                      pady=20)
        
        # Configure column weights
        self.customer_frame.grid_columnconfigure(1, weight=1)
        
    def create_products_section(self, parent):
        # Products Frame (initially hidden)
        self.products_frame = ttk.LabelFrame(parent, 
                                           text="Step 2: Add Products", 
                                           padding=20)
        
        # Current customer display
        self.current_customer_label = ttk.Label(self.products_frame, 
                                              text="", 
                                              font=('Arial', 11, 'bold'),
                                              foreground='green')
        self.current_customer_label.pack(pady=(0, 15))
        
        # Add Product Form
        product_form = ttk.Frame(self.products_frame)
        product_form.pack(fill='x', pady=(0, 15))
        
        # Product Name
        ttk.Label(product_form, 
                 text="Product Name:", 
                 font=('Arial', 10, 'bold')).grid(row=0, column=0, 
                                                 sticky='w', pady=8)
        self.product_name_entry = ttk.Entry(product_form, 
                                          width=30, 
                                          font=('Arial', 11))
        self.product_name_entry.grid(row=0, column=1, 
                                    padx=(10, 20), pady=8, sticky='ew')
        
        # Quantity
        ttk.Label(product_form, 
                 text="Quantity:", 
                 font=('Arial', 10, 'bold')).grid(row=0, column=2, 
                                                 sticky='w', pady=8)
        self.quantity_entry = ttk.Entry(product_form, 
                                       width=15, 
                                       font=('Arial', 11))
        self.quantity_entry.grid(row=0, column=3, 
                                padx=(10, 0), pady=8)
        
        # Unit Price
        ttk.Label(product_form, 
                 text="Unit Price:", 
                 font=('Arial', 10, 'bold')).grid(row=1, column=0, 
                                                 sticky='w', pady=8)
        self.price_entry = ttk.Entry(product_form, 
                                    width=20, 
                                    font=('Arial', 11))
        self.price_entry.grid(row=1, column=1, 
                             padx=(10, 20), pady=8, sticky='w')
        
        # Add Product Button
        add_product_btn = ttk.Button(product_form, 
                                   text="Add Product", 
                                   command=self.add_product,
                                   style='Success.TButton')
        add_product_btn.grid(row=1, column=2, columnspan=2, 
                            padx=10, pady=8)
        
        product_form.grid_columnconfigure(1, weight=1)
        
        # Products List
        list_frame = ttk.LabelFrame(self.products_frame, 
                                  text="Products Added", 
                                  padding=10)
        list_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # Treeview for products
        columns = ('Product', 'Quantity', 'Unit Price', 'Total')
        self.products_tree = ttk.Treeview(list_frame, 
                                        columns=columns, 
                                        show='headings', 
                                        height=8)
        
        for col in columns:
            self.products_tree.heading(col, text=col)
            if col == 'Product':
                self.products_tree.column(col, width=200)
            elif col == 'Quantity':
                self.products_tree.column(col, width=100, anchor='center')
            else:
                self.products_tree.column(col, width=120, anchor='e')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, 
                                 orient='vertical', 
                                 command=self.products_tree.yview)
        self.products_tree.configure(yscrollcommand=scrollbar.set)
        
        self.products_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Control buttons
        buttons_frame = ttk.Frame(self.products_frame)
        buttons_frame.pack(fill='x')
        
        remove_btn = ttk.Button(buttons_frame, 
                               text="Remove Selected", 
                               command=self.remove_product)
        remove_btn.pack(side='left', padx=(0, 10))
        
        clear_btn = ttk.Button(buttons_frame, 
                              text="Clear All Products", 
                              command=self.clear_products)
        clear_btn.pack(side='left', padx=(0, 20))
        
        # Total display
        self.total_frame = ttk.Frame(buttons_frame)
        self.total_frame.pack(side='right')
        
        ttk.Label(self.total_frame, 
                 text="Total Amount:", 
                 font=('Arial', 12, 'bold')).pack(side='left', padx=(0, 10))
        self.total_label = ttk.Label(self.total_frame, 
                                   text="$0.00", 
                                   font=('Arial', 14, 'bold'), 
                                   foreground='red')
        self.total_label.pack(side='left')
        
    def create_invoice_section(self, parent):
        # Invoice Generation Frame (initially hidden)
        self.invoice_frame = ttk.LabelFrame(parent, 
                                          text="Step 3: Generate Invoice", 
                                          padding=20)
        
        # Invoice details
        details_frame = ttk.Frame(self.invoice_frame)
        details_frame.pack(fill='x', pady=(0, 20))
        
        # Invoice number (auto-generated)
        ttk.Label(details_frame, 
                 text="Invoice Number:", 
                 font=('Arial', 10, 'bold')).grid(row=0, column=0, 
                                                 sticky='w', pady=5)
        self.invoice_number_label = ttk.Label(details_frame, 
                                            text="", 
                                            font=('Arial', 11),
                                            foreground='blue')
        self.invoice_number_label.grid(row=0, column=1, 
                                      padx=(15, 0), pady=5, sticky='w')
        
        # Date
        ttk.Label(details_frame, 
                 text="Date:", 
                 font=('Arial', 10, 'bold')).grid(row=1, column=0, 
                                                 sticky='w', pady=5)
        self.date_label = ttk.Label(details_frame, 
                                   text=datetime.now().strftime("%d/%m/%Y"), 
                                   font=('Arial', 11))
        self.date_label.grid(row=1, column=1, 
                            padx=(15, 0), pady=5, sticky='w')
        
        # Generate buttons
        button_frame = ttk.Frame(self.invoice_frame)
        button_frame.pack(fill='x', pady=10)
        
        generate_btn = ttk.Button(button_frame, 
                                 text="Generate Invoice & Save", 
                                 command=self.generate_invoice,
                                 style='Large.TButton')
        generate_btn.pack(side='left', padx=(0, 20))
        
        new_customer_btn = ttk.Button(button_frame, 
                                     text="New Customer", 
                                     command=self.new_customer)
        new_customer_btn.pack(side='left')
        
    def confirm_customer(self):
        # Validate customer information
        shop_name = self.shop_name_entry.get().strip()
        customer_name = self.customer_name_entry.get().strip()
        area = self.area_entry.get().strip()
        
        if not shop_name:
            messagebox.showerror("Error", "Shop Name is required!")
            return
        if not customer_name:
            messagebox.showerror("Error", "Customer Name is required!")
            return
        if not area:
            messagebox.showerror("Error", "Area is required!")
            return
        
        # Store customer data
        self.current_customer = {
            'shop_name': shop_name,
            'customer_name': customer_name,
            'area': area,
            'contact': self.contact_entry.get().strip(),
            'date': datetime.now().strftime("%d/%m/%Y")
        }
        
        # Generate invoice number
        invoice_number = self.generate_invoice_number()
        
        # Update display
        customer_text = (f"Customer: {shop_name} | "
                        f"Owner: {customer_name} | "
                        f"Area: {area}")
        self.current_customer_label.config(text=customer_text)
        self.invoice_number_label.config(text=invoice_number)
        
        # Show products section
        self.products_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        # Hide customer form or make it read-only
        self.confirm_customer_btn.config(text="Customer Confirmed ✓", state='disabled')
        
        # Update status
        self.status_label.config(text="Customer confirmed! Now add products...", 
                               foreground='green')
        
        # Focus on product entry
        self.product_name_entry.focus()
        
    def generate_invoice_number(self):
        # Generate invoice number based on customer and date
        customer_initials = ''.join([word[0].upper() for word in 
                                   self.current_customer['customer_name'].split()])
        date_str = datetime.now().strftime("%y%m%d")
        time_str = datetime.now().strftime("%H%M")
        return f"INV-{customer_initials}-{date_str}-{time_str}"
    
    def add_product(self):
        try:
            product_name = self.product_name_entry.get().strip()
            quantity_str = self.quantity_entry.get().strip()
            price_str = self.price_entry.get().strip()
            
            if not product_name:
                raise ValueError("Product name is required")
            if not quantity_str:
                raise ValueError("Quantity is required")
            if not price_str:
                raise ValueError("Price is required")
            
            quantity = int(quantity_str)
            price = float(price_str)
            
            if quantity <= 0:
                raise ValueError("Quantity must be greater than 0")
            if price < 0:
                raise ValueError("Price cannot be negative")
            
            total = quantity * price
            
            # Add to items list
            item = {
                'product': product_name,
                'quantity': quantity,
                'price': price,
                'total': total
            }
            self.customer_items.append(item)
            
            # Add to treeview
            self.products_tree.insert('', 'end', values=(
                product_name,
                quantity,
                f"${price:.2f}",
                f"${total:.2f}"
            ))
            
            # Clear form
            self.product_name_entry.delete(0, tk.END)
            self.quantity_entry.delete(0, tk.END)
            self.price_entry.delete(0, tk.END)
            
            # Update total
            self.update_total()
            
            # Show invoice section if this is the first item
            if len(self.customer_items) == 1:
                self.invoice_frame.pack(fill='x', pady=(0, 20))
                self.status_label.config(text="Products added! Ready to generate invoice...", 
                                       foreground='blue')
            
            # Focus back to product name
            self.product_name_entry.focus()
            
        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
    
    def remove_product(self):
        selected = self.products_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a product to remove")
            return
        
        for item in selected:
            index = self.products_tree.index(item)
            del self.customer_items[index]
            self.products_tree.delete(item)
        
        self.update_total()
        
        # Hide invoice section if no items
        if not self.customer_items:
            self.invoice_frame.pack_forget()
            self.status_label.config(text="Add products to generate invoice...", 
                                   foreground='orange')
    
    def clear_products(self):
        if self.customer_items and messagebox.askyesno("Confirm", "Clear all products?"):
            self.customer_items.clear()
            for item in self.products_tree.get_children():
                self.products_tree.delete(item)
            self.update_total()
            self.invoice_frame.pack_forget()
            self.status_label.config(text="Products cleared. Add products to continue...", 
                                   foreground='orange')
    
    def update_total(self):
        total = sum(item['total'] for item in self.customer_items)
        self.total_label.config(text=f"${total:.2f}")
    
    def generate_invoice(self):
        if not self.customer_items:
            messagebox.showwarning("No Products", "Please add at least one product")
            return
        
        try:
            # Debug: Print current customer data
            print("DEBUG: Current customer:", self.current_customer)
            print("DEBUG: Customer items:", len(self.customer_items))
            
            # Create filename based on customer name
            safe_name = "".join(c for c in self.current_customer['customer_name'] 
                              if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_name = safe_name.replace(' ', '_')
            filename = f"Invoice_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            
            print(f"DEBUG: Generating file: {filename}")
            
            # Create the Excel invoice
            self.create_excel_invoice(filename)
            
            print(f"DEBUG: File created successfully: {filename}")
            
            # Check if file exists
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                print(f"DEBUG: File exists, size: {file_size} bytes")
            else:
                print("DEBUG: File does not exist after creation!")
            
            # Success message
            success_msg = (f"Invoice generated successfully!\n\n"
                          f"Customer: {self.current_customer['customer_name']}\n"
                          f"Shop: {self.current_customer['shop_name']}\n"
                          f"Total Items: {len(self.customer_items)}\n"
                          f"Total Amount: ${sum(item['total'] for item in self.customer_items):.2f}\n\n"
                          f"File saved as: {filename}\n"
                          f"Location: {os.path.abspath(filename)}")
            
            messagebox.showinfo("Invoice Generated!", success_msg)
            
            self.status_label.config(text=f"Invoice saved: {filename}", 
                                   foreground='green')
            
        except Exception as e:
            error_msg = f"Failed to generate invoice: {str(e)}"
            print(f"DEBUG ERROR: {error_msg}")
            import traceback
            print("DEBUG TRACEBACK:", traceback.format_exc())
            messagebox.showerror("Error", error_msg)
    
    def create_excel_invoice(self, filename):
        print(f"DEBUG: Starting Excel creation for {filename}")
        
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Invoice"
            print("DEBUG: Workbook created")
            
            # Styling
            company_font = Font(name='Arial', size=16, bold=True, color='4472C4')
            title_font = Font(name='Arial', size=24, bold=True, color='4472C4')
            header_font = Font(name='Arial', size=11, bold=True)
            normal_font = Font(name='Arial', size=10)
            total_font = Font(name='Arial', size=14, bold=True, color='FF0000')
            
            # Borders
            thin_border = Border(
                left=Side(style='thin'), right=Side(style='thin'),
                top=Side(style='thin'), bottom=Side(style='thin')
            )
            print("DEBUG: Styles defined")
            
            # Company header
            ws['A1'] = "Your Company Name"  # You can customize this
            ws['A1'].font = company_font
            ws['A2'] = "123 Your Street"
            ws['A3'] = "Your City, State 12345"
            ws['A4'] = "(555) 123-4567"
            print("DEBUG: Company header added")
            
            # Invoice title
            ws['A7'] = "Invoice"
            ws['A7'].font = title_font
            
            # Date
            ws['A8'] = f"Submitted on {self.current_customer['date']}"
            ws['A8'].font = Font(name='Arial', size=10, color='FF0000')
            print("DEBUG: Title and date added")
            
            # Customer information
            ws['A10'] = "Invoice for"
            ws['A10'].font = header_font
            ws['A11'] = self.current_customer['shop_name']
            ws['A11'].font = header_font
            ws['A12'] = self.current_customer['customer_name']
            ws['A13'] = self.current_customer['area']
            if self.current_customer['contact']:
                ws['A14'] = self.current_customer['contact']
            print("DEBUG: Customer info added")
            
            # Invoice details (right side)
            ws['E10'] = "Payable to"
            ws['E10'].font = header_font
            ws['E11'] = self.current_customer['customer_name']
            
            ws['F10'] = f"Invoice # {self.invoice_number_label.cget('text')}"
            ws['F10'].font = header_font
            
            ws['E13'] = "Area"
            ws['E13'].font = header_font
            ws['E14'] = self.current_customer['area']
            
            ws['F13'] = "Date"
            ws['F13'].font = header_font
            ws['F14'] = self.current_customer['date']
            print("DEBUG: Invoice details added")
            
            # Items header
            start_row = 17
            headers = ["Description", "Qty", "Unit price", "Total price"]
            for i, header in enumerate(headers, 1):
                cell = ws.cell(row=start_row, column=i)
                cell.value = header
                cell.font = header_font
                cell.border = thin_border
                cell.alignment = Alignment(horizontal='center')
            print("DEBUG: Items header added")
            
            # Items data
            row = start_row + 1
            total_amount = 0
            for item in self.customer_items:
                ws.cell(row=row, column=1, value=item['product'])
                ws.cell(row=row, column=2, value=item['quantity']).alignment = Alignment(horizontal='center')
                ws.cell(row=row, column=3, value=item['price'])
                ws.cell(row=row, column=4, value=item['total'])
                
                # Add borders
                for col in range(1, 5):
                    ws.cell(row=row, column=col).border = thin_border
                
                total_amount += item['total']
                row += 1
            print(f"DEBUG: {len(self.customer_items)} items added")
            
            # Total
            total_row = row + 2
            ws.cell(row=total_row, column=4, value=total_amount)
            ws.cell(row=total_row, column=4).font = total_font
            ws.cell(row=total_row, column=4).alignment = Alignment(horizontal='right')
            ws.cell(row=total_row, column=4).border = Border(
                left=Side(style='thick'), right=Side(style='thick'),
                top=Side(style='thick'), bottom=Side(style='thick')
            )
            print("DEBUG: Total added")
            
            # Format currency
            for row_num in range(start_row + 1, row):
                ws.cell(row=row_num, column=3).number_format = '"$"#,##0.00'
                ws.cell(row=row_num, column=4).number_format = '"$"#,##0.00'
            ws.cell(row=total_row, column=4).number_format = '"$"#,##0.00'
            print("DEBUG: Currency formatting applied")
            
            # Column widths
            ws.column_dimensions['A'].width = 30
            ws.column_dimensions['B'].width = 10
            ws.column_dimensions['C'].width = 15
            ws.column_dimensions['D'].width = 15
            ws.column_dimensions['E'].width = 15
            ws.column_dimensions['F'].width = 20
            print("DEBUG: Column widths set")
            
            # Save the file
            print(f"DEBUG: Attempting to save file: {filename}")
            wb.save(filename)
            print(f"DEBUG: File saved successfully: {filename}")
            
        except Exception as e:
            print(f"DEBUG: Error in create_excel_invoice: {str(e)}")
            import traceback
            print("DEBUG: Full traceback:", traceback.format_exc())
            raise e
    
    def new_customer(self):
        if messagebox.askyesno("New Customer", 
                              "Start over with a new customer?\n"
                              "This will clear all current data."):
            # Reset everything
            self.current_customer = {}
            self.customer_items = []
            
            # Clear forms
            self.shop_name_entry.delete(0, tk.END)
            self.customer_name_entry.delete(0, tk.END)
            self.area_entry.delete(0, tk.END)
            self.contact_entry.delete(0, tk.END)
            self.product_name_entry.delete(0, tk.END)
            self.quantity_entry.delete(0, tk.END)
            self.price_entry.delete(0, tk.END)
            
            # Clear treeview
            for item in self.products_tree.get_children():
                self.products_tree.delete(item)
            
            # Hide sections
            self.products_frame.pack_forget()
            self.invoice_frame.pack_forget()
            
            # Reset button
            self.confirm_customer_btn.config(text="Confirm Customer Details", 
                                           state='normal')
            
            # Reset status
            self.status_label.config(text="Enter customer details to start...", 
                                   foreground='blue')
            
            # Focus on first field
            self.shop_name_entry.focus()


def main():
    root = tk.Tk()
    
    # Set up modern styling
    style = ttk.Style()
    available_themes = style.theme_names()
    if 'winnative' in available_themes:
        style.theme_use('winnative')
    elif 'clam' in available_themes:
        style.theme_use('clam')
    
    app = CustomerInvoiceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()