import sqlite3
import sys

if len(sys.argv) < 2:
    print("USO: python inspect_sqlite.py <db.sqlite3> [table_name]")
    sys.exit(1)

db = sys.argv[1]
table = sys.argv[2] if len(sys.argv) >= 3 else None

conn = sqlite3.connect(db)
cur = conn.cursor()

if table:
    print(f"\nESTRUCTURA DE TABLA {table}:\n")
    cur.execute(f"PRAGMA table_info({table})")
    for col in cur.fetchall():
        print(col)
else:
    print("\nLISTA DE TABLAS EN LA BASE:\n")
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    for t in cur.fetchall():
        print(t)

conn.close()
