import sqlite3

old_db = "db_old.sqlite3"
new_db = "db.sqlite3"

old_conn = sqlite3.connect(old_db)
new_conn = sqlite3.connect(new_db)

old_cur = old_conn.cursor()
new_cur = new_conn.cursor()

print("Conectando bases...")

# Mapeo directo usando los nombres correctos de tu tabla nueva
insert_query = """
INSERT INTO core_inventory (code, name, category, stock, min_stock, unit, unit_price)
VALUES (?, ?, ?, ?, ?, ?, ?)
"""

print("Importando inventario...\n")

old_cur.execute("SELECT code, nombre, descripcion, cantidad, min_stock, proveedor, buy_price FROM core_product")
rows = old_cur.fetchall()

print(f"Productos encontrados: {len(rows)}\n")

for row in rows:
    code = row[0]
    name = row[1]
    category = row[2] or "Sin categoría"
    stock = row[3]
    min_stock = row[4]
    unit = row[5] or "unidad"
    unit_price = row[6] or 0

    new_cur.execute(insert_query, (code, name, category, stock, min_stock, unit, unit_price))

new_conn.commit()

print("\nIMPORTACIÓN COMPLETA ✔")

old_conn.close()
new_conn.close()
