import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
from order_management import (
    append_order, iter_orders, filter_orders, export_orders, 
    summarize_sales, parse_date_str
)


class OrderManagementGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Order Management System")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_add_order_tab()
        self.create_view_orders_tab()
        self.create_search_tab()
        self.create_dashboard_tab()
        
    def create_add_order_tab(self):
        # Add Order Tab
        add_frame = ttk.Frame(self.notebook)
        self.notebook.add(add_frame, text="Add Order")
        
        # Create main container with padding
        main_container = ttk.Frame(add_frame)
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_container, text="Add New Order", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Form frame
        form_frame = ttk.LabelFrame(main_container, text="Order Details", padding=20)
        form_frame.pack(fill='x', pady=(0, 20))
        
        # Customer Name
        ttk.Label(form_frame, text="Customer Name:").grid(row=0, column=0, 
                                                          sticky='w', pady=5)
        self.customer_entry = ttk.Entry(form_frame, width=40)
        self.customer_entry.grid(row=0, column=1, padx=(10, 0), pady=5, sticky='ew')
        
        # Contact
        ttk.Label(form_frame, text="Contact (Phone/Email):").grid(row=1, column=0, 
                                                                  sticky='w', pady=5)
        self.contact_entry = ttk.Entry(form_frame, width=40)
        self.contact_entry.grid(row=1, column=1, padx=(10, 0), pady=5, sticky='ew')
        
        # Product Name
        ttk.Label(form_frame, text="Product Name:").grid(row=2, column=0, 
                                                         sticky='w', pady=5)
        self.product_entry = ttk.Entry(form_frame, width=40)
        self.product_entry.grid(row=2, column=1, padx=(10, 0), pady=5, sticky='ew')
        
        # Quantity
        ttk.Label(form_frame, text="Quantity:").grid(row=3, column=0, sticky='w', pady=5)
        self.quantity_entry = ttk.Entry(form_frame, width=40)
        self.quantity_entry.grid(row=3, column=1, padx=(10, 0), pady=5, sticky='ew')
        
        # Price
        ttk.Label(form_frame, text="Unit Price:").grid(row=4, column=0, sticky='w', pady=5)
        self.price_entry = ttk.Entry(form_frame, width=40)
        self.price_entry.grid(row=4, column=1, padx=(10, 0), pady=5, sticky='ew')
        
        # Configure column weight for responsive design
        form_frame.grid_columnconfigure(1, weight=1)
        
        # Buttons frame
        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill='x')
        
        # Add Order Button
        add_button = ttk.Button(button_frame, text="Add Order", 
                               command=self.add_order, style='Accent.TButton')
        add_button.pack(side='left', padx=(0, 10))
        
        # Clear Button
        clear_button = ttk.Button(button_frame, text="Clear Form", 
                                 command=self.clear_form)
        clear_button.pack(side='left')
        
        # Status label
        self.status_label = ttk.Label(main_container, text="Ready to add orders...", 
                                     foreground='green')
        self.status_label.pack(pady=(10, 0))
        
    def create_view_orders_tab(self):
        # View Orders Tab
        view_frame = ttk.Frame(self.notebook)
        self.notebook.add(view_frame, text="View Orders")
        
        # Controls frame
        controls_frame = ttk.Frame(view_frame)
        controls_frame.pack(fill='x', padx=10, pady=10)
        
        # Refresh button
        refresh_button = ttk.Button(controls_frame, text="Refresh", 
                                   command=self.load_orders)
        refresh_button.pack(side='left', padx=(0, 10))
        
        # Export button
        export_button = ttk.Button(controls_frame, text="Export to Excel", 
                                  command=self.export_orders)
        export_button.pack(side='left')
        
        # Orders treeview
        columns = ('Order ID', 'Timestamp', 'Customer', 'Contact', 'Product', 
                  'Quantity', 'Unit Price', 'Total Price')
        
        self.orders_tree = ttk.Treeview(view_frame, columns=columns, show='headings', 
                                       height=15)
        
        # Configure columns
        for col in columns:
            self.orders_tree.heading(col, text=col)
            if col in ['Order ID', 'Quantity']:
                self.orders_tree.column(col, width=80, anchor='center')
            elif col in ['Unit Price', 'Total Price']:
                self.orders_tree.column(col, width=100, anchor='e')
            else:
                self.orders_tree.column(col, width=120)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(view_frame, orient='vertical', 
                                   command=self.orders_tree.yview)
        h_scrollbar = ttk.Scrollbar(view_frame, orient='horizontal', 
                                   command=self.orders_tree.xview)
        self.orders_tree.configure(yscrollcommand=v_scrollbar.set, 
                                  xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.orders_tree.pack(side='left', fill='both', expand=True, padx=(10, 0))
        v_scrollbar.pack(side='right', fill='y', padx=(0, 10))
        h_scrollbar.pack(side='bottom', fill='x', padx=10)
        
        # Summary frame
        summary_frame = ttk.LabelFrame(view_frame, text="Summary", padding=10)
        summary_frame.pack(fill='x', padx=10, pady=10)
        
        self.summary_label = ttk.Label(summary_frame, text="Total Orders: 0 | Total Sales: $0.00")
        self.summary_label.pack()
        
    def create_search_tab(self):
        # Search Tab
        search_frame = ttk.Frame(self.notebook)
        self.notebook.add(search_frame, text="Search Orders")
        
        # Search controls
        search_controls = ttk.LabelFrame(search_frame, text="Search Filters", padding=10)
        search_controls.pack(fill='x', padx=10, pady=10)
        
        # Customer search
        ttk.Label(search_controls, text="Customer Name:").grid(row=0, column=0, 
                                                              sticky='w', pady=5)
        self.search_customer = ttk.Entry(search_controls, width=30)
        self.search_customer.grid(row=0, column=1, padx=(10, 20), pady=5, sticky='ew')
        
        # Product search
        ttk.Label(search_controls, text="Product Name:").grid(row=0, column=2, 
                                                             sticky='w', pady=5)
        self.search_product = ttk.Entry(search_controls, width=30)
        self.search_product.grid(row=0, column=3, padx=(10, 0), pady=5, sticky='ew')
        
        # Date filters
        ttk.Label(search_controls, text="From Date (YYYY-MM-DD):").grid(row=1, column=0, 
                                                                        sticky='w', pady=5)
        self.search_from_date = ttk.Entry(search_controls, width=30)
        self.search_from_date.grid(row=1, column=1, padx=(10, 20), pady=5, sticky='ew')
        
        ttk.Label(search_controls, text="To Date (YYYY-MM-DD):").grid(row=1, column=2, 
                                                                     sticky='w', pady=5)
        self.search_to_date = ttk.Entry(search_controls, width=30)
        self.search_to_date.grid(row=1, column=3, padx=(10, 0), pady=5, sticky='ew')
        
        # Search button
        search_button = ttk.Button(search_controls, text="Search", 
                                  command=self.search_orders)
        search_button.grid(row=2, column=1, pady=10, sticky='w')
        
        # Clear search button
        clear_search_button = ttk.Button(search_controls, text="Clear", 
                                        command=self.clear_search)
        clear_search_button.grid(row=2, column=2, pady=10, sticky='w')
        
        # Configure grid weights
        search_controls.grid_columnconfigure(1, weight=1)
        search_controls.grid_columnconfigure(3, weight=1)
        
        # Search results treeview
        columns = ('Order ID', 'Timestamp', 'Customer', 'Contact', 'Product', 
                  'Quantity', 'Unit Price', 'Total Price')
        
        self.search_tree = ttk.Treeview(search_frame, columns=columns, show='headings', 
                                       height=12)
        
        # Configure columns (same as view orders)
        for col in columns:
            self.search_tree.heading(col, text=col)
            if col in ['Order ID', 'Quantity']:
                self.search_tree.column(col, width=80, anchor='center')
            elif col in ['Unit Price', 'Total Price']:
                self.search_tree.column(col, width=100, anchor='e')
            else:
                self.search_tree.column(col, width=120)
        
        # Scrollbars for search results
        search_v_scrollbar = ttk.Scrollbar(search_frame, orient='vertical', 
                                          command=self.search_tree.yview)
        search_h_scrollbar = ttk.Scrollbar(search_frame, orient='horizontal', 
                                          command=self.search_tree.xview)
        self.search_tree.configure(yscrollcommand=search_v_scrollbar.set, 
                                  xscrollcommand=search_h_scrollbar.set)
        
        # Pack search treeview and scrollbars
        self.search_tree.pack(side='left', fill='both', expand=True, padx=(10, 0))
        search_v_scrollbar.pack(side='right', fill='y', padx=(0, 10))
        search_h_scrollbar.pack(side='bottom', fill='x', padx=10)
        
        # Search summary
        search_summary_frame = ttk.LabelFrame(search_frame, text="Search Results", padding=10)
        search_summary_frame.pack(fill='x', padx=10, pady=10)
        
        self.search_summary_label = ttk.Label(search_summary_frame, 
                                             text="Enter search criteria and click Search")
        self.search_summary_label.pack()
        
    def create_dashboard_tab(self):
        # Dashboard Tab
        dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(dashboard_frame, text="Dashboard")
        
        # Controls
        dash_controls = ttk.LabelFrame(dashboard_frame, text="Summary Options", padding=10)
        dash_controls.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(dash_controls, text="Period:").pack(side='left', padx=(0, 10))
        
        self.period_var = tk.StringVar(value="daily")
        period_combo = ttk.Combobox(dash_controls, textvariable=self.period_var, 
                                   values=["daily", "weekly", "monthly"], 
                                   state="readonly", width=15)
        period_combo.pack(side='left', padx=(0, 10))
        
        generate_button = ttk.Button(dash_controls, text="Generate Summary", 
                                    command=self.generate_dashboard)
        generate_button.pack(side='left')
        
        # Dashboard treeview
        dash_columns = ('Period', 'Sales Total')
        self.dashboard_tree = ttk.Treeview(dashboard_frame, columns=dash_columns, 
                                          show='headings', height=15)
        
        for col in dash_columns:
            self.dashboard_tree.heading(col, text=col)
            if col == 'Sales Total':
                self.dashboard_tree.column(col, width=150, anchor='e')
            else:
                self.dashboard_tree.column(col, width=200)
        
        # Scrollbar for dashboard
        dash_scrollbar = ttk.Scrollbar(dashboard_frame, orient='vertical', 
                                      command=self.dashboard_tree.yview)
        self.dashboard_tree.configure(yscrollcommand=dash_scrollbar.set)
        
        self.dashboard_tree.pack(side='left', fill='both', expand=True, padx=(10, 0))
        dash_scrollbar.pack(side='right', fill='y', padx=(0, 10))
        
    def add_order(self):
        try:
            # Validate inputs
            customer = self.customer_entry.get().strip()
            contact = self.contact_entry.get().strip()
            product = self.product_entry.get().strip()
            quantity_str = self.quantity_entry.get().strip()
            price_str = self.price_entry.get().strip()
            
            if not customer:
                raise ValueError("Customer name is required")
            if not product:
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
            
            # Add the order
            order_id, total = append_order(customer, contact, product, quantity, price)
            
            # Show success message
            self.status_label.config(
                text=f"Order #{order_id} added successfully! Total: ${total:.2f}",
                foreground='green'
            )
            
            # Clear the form
            self.clear_form()
            
            # Refresh the orders view if it's been loaded
            if hasattr(self, 'orders_loaded'):
                self.load_orders()
            
        except ValueError as e:
            self.status_label.config(text=f"Error: {str(e)}", foreground='red')
            messagebox.showerror("Input Error", str(e))
        except PermissionError as e:
            error_msg = ("Cannot access orders.xlsx file!\n\n"
                        "Possible solutions:\n"
                        "1. Close Excel if you have orders.xlsx open\n"
                        "2. Make sure you have write permissions to this folder\n"
                        "3. Try running as administrator\n\n"
                        f"Technical error: {str(e)}")
            self.status_label.config(text="File access denied - see dialog for help", foreground='red')
            messagebox.showerror("File Access Error", error_msg)
        except Exception as e:
            error_msg = f"An unexpected error occurred: {str(e)}"
            if "Permission denied" in str(e) or "[Errno 13]" in str(e):
                error_msg += ("\n\nThis looks like a file permission issue.\n"
                             "Please close Excel if orders.xlsx is open, or run as administrator.")
            self.status_label.config(text=f"Unexpected error: {str(e)}", foreground='red')
            messagebox.showerror("Error", error_msg)
    
    def clear_form(self):
        self.customer_entry.delete(0, tk.END)
        self.contact_entry.delete(0, tk.END)
        self.product_entry.delete(0, tk.END)
        self.quantity_entry.delete(0, tk.END)
        self.price_entry.delete(0, tk.END)
        self.status_label.config(text="Form cleared. Ready for new order.", 
                                foreground='blue')
    
    def load_orders(self):
        try:
            # Clear existing items
            for item in self.orders_tree.get_children():
                self.orders_tree.delete(item)
            
            # Load orders
            orders = list(iter_orders())
            total_sales = 0.0
            
            for order in orders:
                # Format timestamp
                timestamp = order.get('timestamp', '')
                if isinstance(timestamp, str) and 'T' in timestamp:
                    timestamp = timestamp.replace('T', ' ')
                
                self.orders_tree.insert('', 'end', values=(
                    order.get('order_id', ''),
                    timestamp,
                    order.get('customer_name', ''),
                    order.get('contact', ''),
                    order.get('product_name', ''),
                    order.get('quantity', 0),
                    f"${order.get('price', 0.0):.2f}",
                    f"${order.get('total_price', 0.0):.2f}"
                ))
                total_sales += order.get('total_price', 0.0)
            
            # Update summary
            self.summary_label.config(
                text=f"Total Orders: {len(orders)} | Total Sales: ${total_sales:.2f}"
            )
            
            self.orders_loaded = True
            
        except PermissionError as e:
            error_msg = ("Cannot access orders.xlsx file!\n\n"
                        "Please close Excel if you have orders.xlsx open and try again.")
            messagebox.showerror("File Access Error", error_msg)
        except Exception as e:
            error_msg = f"Failed to load orders: {str(e)}"
            if "Permission denied" in str(e) or "[Errno 13]" in str(e):
                error_msg += "\n\nPlease close Excel if orders.xlsx is open."
            messagebox.showerror("Error", error_msg)
    
    def export_orders(self):
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="Save Orders Export"
            )
            
            if filename:
                orders = list(iter_orders())
                export_orders(orders, filename)
                messagebox.showinfo("Export Complete", 
                                  f"Exported {len(orders)} orders to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {str(e)}")
    
    def search_orders(self):
        try:
            # Get search criteria
            customer_query = self.search_customer.get().strip() or None
            product_query = self.search_product.get().strip() or None
            since_str = self.search_from_date.get().strip() or None
            until_str = self.search_to_date.get().strip() or None
            
            since = parse_date_str(since_str) if since_str else None
            until = parse_date_str(until_str) if until_str else None
            
            # Clear existing search results
            for item in self.search_tree.get_children():
                self.search_tree.delete(item)
            
            # Filter orders
            filtered_orders = filter_orders(
                iter_orders(),
                customer_query=customer_query,
                product_query=product_query,
                since=since,
                until=until
            )
            
            total_sales = 0.0
            
            # Populate search results
            for order in filtered_orders:
                timestamp = order.get('timestamp', '')
                if isinstance(timestamp, str) and 'T' in timestamp:
                    timestamp = timestamp.replace('T', ' ')
                
                self.search_tree.insert('', 'end', values=(
                    order.get('order_id', ''),
                    timestamp,
                    order.get('customer_name', ''),
                    order.get('contact', ''),
                    order.get('product_name', ''),
                    order.get('quantity', 0),
                    f"${order.get('price', 0.0):.2f}",
                    f"${order.get('total_price', 0.0):.2f}"
                ))
                total_sales += order.get('total_price', 0.0)
            
            # Update search summary
            self.search_summary_label.config(
                text=f"Found {len(filtered_orders)} orders | Total Sales: ${total_sales:.2f}"
            )
            
        except Exception as e:
            messagebox.showerror("Search Error", f"Search failed: {str(e)}")
    
    def clear_search(self):
        self.search_customer.delete(0, tk.END)
        self.search_product.delete(0, tk.END)
        self.search_from_date.delete(0, tk.END)
        self.search_to_date.delete(0, tk.END)
        
        # Clear search results
        for item in self.search_tree.get_children():
            self.search_tree.delete(item)
        
        self.search_summary_label.config(text="Search cleared. Enter new criteria.")
    
    def generate_dashboard(self):
        try:
            # Clear existing dashboard data
            for item in self.dashboard_tree.get_children():
                self.dashboard_tree.delete(item)
            
            # Generate summary
            period = self.period_var.get()
            orders = list(iter_orders())
            summary_data = summarize_sales(orders, period)
            
            # Populate dashboard
            for row in summary_data:
                self.dashboard_tree.insert('', 'end', values=(
                    row['period'],
                    f"${row['sales_total']:.2f}"
                ))
            
        except Exception as e:
            messagebox.showerror("Dashboard Error", f"Failed to generate dashboard: {str(e)}")


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
    
    # Create and run the application
    app = OrderManagementGUI(root)
    
    # Load orders on startup
    app.load_orders()
    
    root.mainloop()


if __name__ == "__main__":
    main()