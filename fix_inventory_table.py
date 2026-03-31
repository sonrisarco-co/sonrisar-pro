import sqlite3

DB = "db.sqlite3"

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("Eliminando tabla rota core_inventoryitem si existe...")
cur.execute("DROP TABLE IF EXISTS core_inventoryitem;")

print("Recreando tabla correcta core_inventoryitem...")
cur.execute("""
CREATE TABLE core_inventoryitem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(150) NOT NULL,
    code VARCHAR(50) NOT NULL,
    category VARCHAR(100) NOT NULL,
    stock INTEGER NOT NULL,
    min_stock INTEGER NOT NULL,
    unit VARCHAR(20) NOT NULL,
    unit_price DECIMAL NOT NULL
);
""")

conn.commit()
conn.close()

print("TABLA INVENTARIO RECREADA CORRECTAMENTE ✔")
