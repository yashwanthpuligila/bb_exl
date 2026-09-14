import sqlite3
from pathlib import Path

db_path = Path("web/invoice_learning.db")
print(f"Checking DB: {db_path.resolve()} (exists: {db_path.exists()}, size: {db_path.stat().st_size if db_path.exists() else 0} bytes)")

if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]
    print("Local SQLite Tables & Row Counts:")
    for t in tables:
        cnt = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        print(f"  {t}: {cnt} rows")
