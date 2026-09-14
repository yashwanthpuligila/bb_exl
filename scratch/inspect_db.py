import sqlite3

def inspect():
    conn = sqlite3.connect('web/invoice_learning.db')
    cursor = conn.cursor()
    tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    print('TABLES IN SQLITE DB:', tables)
    for t in tables:
        count = cursor.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        cursor.execute(f'PRAGMA table_info("{t}")')
        cols = [f"{col[1]} ({col[2]})" for col in cursor.fetchall()]
        print(f"\n--- Table: {t} (rows: {count}) ---")
        print("Columns:", ", ".join(cols))
        
        # print sample row
        cursor.execute(f'SELECT * FROM "{t}" LIMIT 1')
        sample = cursor.fetchone()
        if sample:
            print("Sample row:", sample)

if __name__ == '__main__':
    inspect()
