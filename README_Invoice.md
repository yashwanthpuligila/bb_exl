# Professional Invoice Generator

A comprehensive invoice generator that creates professional invoices exactly like the format you requested - with company header, customer details, itemized products, and proper totals.

## Features

### 📋 **Complete Invoice Information**
- **Company Details**: Name, address, phone
- **Customer Information**: Shop name, customer name, area, contact
- **Invoice Details**: Invoice number, due date, project reference
- **Product Items**: Description, quantity, unit price, total price
- **Professional Totals**: Subtotal, adjustments, final total

### 🎨 **Professional Styling**
- Matches the exact layout from your reference image
- Blue company header
- Red submission date and total amount
- Professional borders and formatting
- Currency formatting ($X,XXX.XX)

### 📊 **Four Easy Steps**

#### **Step 1: Company Info Tab**
Set up your company details:
- Company Name
- Address Line 1 & 2
- Phone Number

#### **Step 2: Customer Info Tab**
Enter customer details:
- **Shop Name** (main customer)
- **Customer Name** (shop owner/contact person)
- **Area** (location/district)
- **Contact** (phone/email)
- **Project/Reference** (order reference)

#### **Step 3: Invoice Items Tab**
Add products to the invoice:
- **Product Description** (what you're selling)
- **Quantity** (how many)
- **Unit Price** (price per item)
- **Automatic Total Calculation**

**Item Management:**
- ✅ Add multiple items
- ✅ Remove selected items  
- ✅ Clear all items
- ✅ Real-time subtotal calculation
- ✅ Adjustments (discounts/charges)

#### **Step 4: Generate Invoice Tab**
Finalize and create the invoice:
- Set invoice number
- Set due date
- Add notes (optional)
- Preview before generating
- Save as professional Excel file

## 🚀 **How to Use**

### **Quick Start:**
1. Double-click `run_invoice.bat`
2. Fill in company details (Step 1)
3. Enter customer information (Step 2)
4. Add invoice items (Step 3)
5. Generate the invoice (Step 4)

### **Detailed Workflow:**

#### **Setting Up Company Info:**
```
Company Name: ABC Trading Company
Address 1: 123 Business Street  
Address 2: Commerce City, ST 12345
Phone: (555) 123-4567
```

#### **Adding Customer Info:**
```
Shop Name: Super Market Plus
Customer Name: Ahmed Khan
Area: Downtown Commercial District
Contact: (555) 987-6543
Project: Monthly Supply Order
```

#### **Adding Items:**
```
Product: Premium Rice Bags (50kg)
Quantity: 10
Unit Price: 45.00
→ Total: $450.00 (calculated automatically)

Product: Cooking Oil (5L bottles)
Quantity: 24  
Unit Price: 12.50
→ Total: $300.00
```

#### **Final Invoice:**
- Subtotal: $750.00
- Adjustment: -$50.00 (discount)
- **Total: $700.00**

## 📄 **Generated Invoice Format**

The generated Excel invoice includes:

```
[Company Header - Blue]
ABC Trading Company
123 Business Street
Commerce City, ST 12345
(555) 123-4567

Invoice [Large Blue Title]
Submitted on 09/28/2025 [Red]

Invoice for          |  Payable to      | Invoice # 20250928001
Super Market Plus    |  Ahmed Khan      | 
Ahmed Khan          |                  | Due date: 10/28/2025
Downtown Commercial |  Project         |
                    |  Monthly Supply  |

Description          | Qty | Unit price | Total price
Premium Rice (50kg)  |  10 |    $45.00  |   $450.00
Cooking Oil (5L)     |  24 |    $12.50  |   $300.00

                              Subtotal    $750.00
                              Adjustments  -$50.00
                              
                              $700.00 [Red, Boxed]
```

## 💡 **Key Features**

### **Professional Appearance:**
- ✅ Exact replica of your reference invoice
- ✅ Blue company header and invoice title
- ✅ Red submission date and final total
- ✅ Professional table formatting with borders
- ✅ Currency formatting throughout

### **Business Functionality:**
- ✅ Automatic invoice numbering
- ✅ Date formatting
- ✅ Multi-item support
- ✅ Quantity × Price calculations
- ✅ Subtotal and adjustments
- ✅ Professional Excel output

### **User Experience:**
- ✅ Tab-based interface (easy navigation)
- ✅ Form validation (prevents errors)
- ✅ Live preview before generating
- ✅ Real-time total calculations
- ✅ Save to any location

## 🔧 **Requirements**

- Python 3.6+
- openpyxl library (already in requirements.txt)
- tkinter (built into Python)

## 📁 **File Structure**

```
y:\bb_exl\
├── invoice_generator.py     # Main invoice application
├── run_invoice.bat         # Easy launcher
├── requirements.txt        # Dependencies
└── README_Invoice.md      # This guide
```

## 🎯 **Perfect For:**

- **Retail Shops** - Generate customer bills
- **Wholesale Business** - Create supplier invoices  
- **Small Businesses** - Professional invoicing
- **Freelancers** - Client billing
- **Service Providers** - Service invoices

## 🚀 **Quick Tips:**

1. **Fill company info once** - it's saved for future invoices
2. **Use adjustments** for discounts or additional charges
3. **Preview first** - check everything before generating
4. **Save with meaningful names** - like "Invoice_CustomerName_Date"
5. **Keep invoices organized** - use folders by month/customer

---

**Ready to create professional invoices just like your reference image! 🎯**