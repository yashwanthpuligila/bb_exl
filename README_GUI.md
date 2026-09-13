# Order Management System - GUI

A simple graphical user interface for managing customer orders with Excel backend storage.

## Features

The GUI provides an easy-to-use interface with four main tabs:

### 1. Add Order Tab
- **Customer Name**: Enter the customer's full name (required)
- **Contact**: Phone number or email address (optional)
- **Product Name**: Name of the product being ordered (required)
- **Quantity**: Number of items (required, must be > 0)
- **Unit Price**: Price per item (required, must be ≥ 0)

**Features:**
- Form validation to ensure all required fields are filled
- Automatic calculation of total price
- Clear form button to reset all fields
- Real-time status updates

### 2. View Orders Tab
- View all orders in a table format
- Shows Order ID, timestamp, customer details, product info, and pricing
- Refresh button to reload data
- Export to Excel functionality
- Summary showing total orders and sales

### 3. Search Orders Tab
- **Filter by Customer**: Enter partial customer name
- **Filter by Product**: Enter partial product name  
- **Date Range**: Filter orders between specific dates (YYYY-MM-DD format)
- View filtered results in the same table format
- Clear search button to reset filters

### 4. Dashboard Tab
- Generate sales summaries by period:
  - Daily: Sales totals by day
  - Weekly: Sales totals by week
  - Monthly: Sales totals by month
- Easy-to-read summary tables

## How to Run

### Method 1: Double-click the batch file
```
run_gui.bat
```

### Method 2: Run from command line
```bash
cd y:\bb_exl
python order_gui.py
```

### Method 3: Run from PowerShell
```powershell
cd y:\bb_exl
python order_gui.py
```

## Requirements

- Python 3.6 or higher
- openpyxl library (install with: `pip install -r requirements.txt`)

## Data Storage

- All orders are stored in `orders.xlsx` in the same directory
- The Excel file is automatically created if it doesn't exist
- Data is saved immediately when you add new orders

## Tips for Usage

1. **Adding Orders**: Fill in all required fields (Customer Name, Product Name, Quantity, Price) before clicking "Add Order"

2. **Searching**: You can use partial matches for customer and product names. Leave fields empty to ignore those filters.

3. **Date Filtering**: Use YYYY-MM-DD format (e.g., 2025-09-28). You can use just "From Date" or just "To Date" if needed.

4. **Exporting**: Click "Export to Excel" in the View Orders tab to save filtered data to a new Excel file

5. **Dashboard**: Select different time periods to see sales patterns over time

## Error Handling

- The GUI validates all inputs and shows helpful error messages
- If the Excel file gets corrupted, delete `orders.xlsx` and restart - a new file will be created
- All operations are safely handled with try-catch blocks

## Keyboard Shortcuts

- **Tab**: Navigate between form fields
- **Enter**: Submit form (when in Add Order tab)
- **Escape**: Clear current field

---

**Note**: The GUI uses tkinter which comes built-in with Python, so no additional GUI libraries are needed.