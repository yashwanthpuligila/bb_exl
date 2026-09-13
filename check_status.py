import os
from order_management import check_excel_lock, is_file_accessible, WORKBOOK_FILENAME

def check_file_status():
    print("=" * 50)
    print("Order Management - File Status Check")
    print("=" * 50)
    
    # Check if orders.xlsx exists
    if os.path.exists(WORKBOOK_FILENAME):
        print(f"✓ {WORKBOOK_FILENAME} exists")
    else:
        print(f"✗ {WORKBOOK_FILENAME} does not exist (will be created)")
    
    # Check for Excel lock
    lock_msg = check_excel_lock()
    if lock_msg:
        print(f"✗ Excel Lock Detected: {lock_msg}")
    else:
        print("✓ No Excel lock detected")
    
    # Check file accessibility
    if os.path.exists(WORKBOOK_FILENAME):
        if is_file_accessible(WORKBOOK_FILENAME):
            print("✓ File is accessible for writing")
        else:
            print("✗ File is NOT accessible for writing")
    
    print("\n" + "=" * 50)
    
    # List all files in directory for debugging
    print("Files in current directory:")
    for file in os.listdir('.'):
        if file.startswith('~$'):
            print(f"  {file} (Excel lock file)")
        elif file.endswith('.xlsx'):
            print(f"  {file} (Excel file)")
        else:
            print(f"  {file}")
    
    print("=" * 50)

if __name__ == "__main__":
    check_file_status()