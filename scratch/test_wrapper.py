import os
import sqlite3
from datetime import datetime, date

class SqliteCursorWrapper:
    def __init__(self, raw_cursor):
        self._raw_cursor = raw_cursor
        
    def execute(self, sql, params=None):
        if params is not None:
            self._raw_cursor.execute(sql, params)
        else:
            self._raw_cursor.execute(sql)
        return self
        
    def fetchone(self):
        return self._raw_cursor.fetchone()
        
    def fetchall(self):
        return self._raw_cursor.fetchall()
        
    def fetchmany(self, size=None):
        return self._raw_cursor.fetchmany(size) if size else self._raw_cursor.fetchmany()
        
    @property
    def rowcount(self):
        return self._raw_cursor.rowcount
        
    @property
    def description(self):
        return self._raw_cursor.description
        
    def __iter__(self):
        return iter(self._raw_cursor)

class SqliteConnWrapper:
    def __init__(self, db_path):
        self._raw_conn = sqlite3.connect(str(db_path), timeout=15)
        self._raw_conn.row_factory = sqlite3.Row
        self._raw_conn.execute("PRAGMA journal_mode=WAL")
        self.row_factory = sqlite3.Row
        
    def cursor(self):
        return SqliteCursorWrapper(self._raw_conn.cursor())
        
    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur
        
    def commit(self):
        self._raw_conn.commit()
        
    def rollback(self):
        self._raw_conn.rollback()
        
    def close(self):
        self._raw_conn.close()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            try:
                self.rollback()
            except Exception:
                pass
        else:
            try:
                self.commit()
            except Exception:
                pass
        self.close()

# Test queries
with SqliteConnWrapper('web/invoice_learning.db') as conn:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM customers")
    print("Customer count via execute().fetchone():", cur.fetchone()[0])
    
    # Test chained execute().fetchone()[0]
    cnt = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    print("Product count via conn.execute().fetchone():", cnt)
    
    # Test dict(row)
    cur.execute("SELECT * FROM customers LIMIT 1")
    row = cur.fetchone()
    print("Row as dict:", dict(row))
    print("Row access by index:", row[0], row[1])
    print("Row access by name:", row['display_name'])
    
    # Test table info
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print("Tables:", tables)
    cur.execute('PRAGMA table_info("customers")')
    cols = [c[1] for c in cur.fetchall()]
    print("Columns in customers:", cols)
    
print("SQLite wrapper test SUCCESS!")

