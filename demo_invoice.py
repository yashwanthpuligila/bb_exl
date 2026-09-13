"""
Demo script to show how the Professional Invoice Generator works
"""

def demo_invoice_data():
    """
    Sample data that you can use to test the invoice generator
    """
    
    print("=== PROFESSIONAL INVOICE GENERATOR DEMO ===\n")
    
    print("📋 SAMPLE DATA TO TEST:")
    print("-" * 40)
    
    print("\n1️⃣ COMPANY INFORMATION:")
    print("   Company Name: ABC Trading Company")
    print("   Address 1: 123 Business Street")  
    print("   Address 2: Commerce City, ST 12345")
    print("   Phone: (555) 123-4567")
    
    print("\n2️⃣ CUSTOMER INFORMATION:")
    print("   Shop Name: Super Market Plus")
    print("   Customer Name: Ahmed Khan")
    print("   Area: Downtown Commercial District")
    print("   Contact: (555) 987-6543")
    print("   Project: Monthly Supply Order")
    
    print("\n3️⃣ SAMPLE INVOICE ITEMS:")
    print("   Item 1:")
    print("     Description: Premium Rice Bags (50kg)")
    print("     Quantity: 10")
    print("     Unit Price: $45.00")
    print("     Total: $450.00")
    print()
    print("   Item 2:")
    print("     Description: Cooking Oil (5L bottles)")
    print("     Quantity: 24")
    print("     Unit Price: $12.50") 
    print("     Total: $300.00")
    print()
    print("   Item 3:")
    print("     Description: Sugar Bags (25kg)")
    print("     Quantity: 8")
    print("     Unit Price: $25.00")
    print("     Total: $200.00")
    
    print("\n4️⃣ INVOICE TOTALS:")
    print("   Subtotal: $950.00")
    print("   Adjustment: -$50.00 (discount)")
    print("   FINAL TOTAL: $900.00")
    
    print("\n" + "=" * 50)
    print("🎯 STEPS TO CREATE THIS INVOICE:")
    print("1. Run: python invoice_generator.py")
    print("2. Fill in the Company Info tab with data above")
    print("3. Fill in the Customer Info tab")  
    print("4. Add the 3 items in the Invoice Items tab")
    print("5. Set adjustment to -50.00")
    print("6. Go to Generate Invoice tab")
    print("7. Click 'Preview Invoice' to see how it looks")
    print("8. Click 'Generate Excel Invoice' to save it")
    print("=" * 50)
    
    print("\n📄 THE GENERATED INVOICE WILL LOOK EXACTLY")
    print("   LIKE YOUR REFERENCE IMAGE WITH:")
    print("   ✅ Blue company header")
    print("   ✅ Professional invoice title") 
    print("   ✅ Customer details on left")
    print("   ✅ Invoice info on right")
    print("   ✅ Itemized products table")
    print("   ✅ Subtotal, adjustments, and red total")
    print("   ✅ Professional Excel formatting")
    

if __name__ == "__main__":
    demo_invoice_data()
    
    print("\n🚀 Ready to start? Run one of these:")
    print("   • Double-click: run_invoice.bat")
    print("   • Command: python invoice_generator.py")
    print("\n💡 The app is already running if you started it!")