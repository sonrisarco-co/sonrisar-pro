import sqlite3

# Abrir base vieja
conn = sqlite3.connect("db_old.sqlite3")
cur = conn.cursor()

print("\nMOSTRANDO ESTRUCTURA DE core_patient:\n")
rows = cur.execute("PRAGMA table_info(core_patient);").fetchall()

for r in rows:
    print(r)

print("\nLISTA DE TABLAS EN LA BASE:")
tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
for t in tables:
    print(t)

conn.close()
