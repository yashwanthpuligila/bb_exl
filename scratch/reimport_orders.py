import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))
import learning_db

with learning_db.get_connection() as conn:
    c = conn.cursor()
    c.execute("DELETE FROM invoices WHERE invoice_number = 'orders'")
    c.execute("DELETE FROM invoice_items WHERE invoice_number = 'orders'")
    c.execute("DELETE FROM processed_invoices WHERE invoice_file = 'orders.xlsx'")
    c.execute("DELETE FROM customers WHERE normalized_name = 'wholesale customer'")
    conn.commit()

learning_db.import_historical_data([str(Path(__file__).resolve().parent.parent)])
print("Re-imported orders.xlsx successfully!")
