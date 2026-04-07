import sqlite3

old_db = "db_old.sqlite3"
new_db = "db.sqlite3"

old_conn = sqlite3.connect(old_db)
new_conn = sqlite3.connect(new_db)

old_cur = old_conn.cursor()
new_cur = new_conn.cursor()

print("Conectando bases...")
print("Importando inventario...\n")

# Consulta SOLO las columnas que sabemos que sí existen
old_cur.execute("""
    SELECT code, nombre, descripcion, cantidad, min_stock, buy_price
    FROM core_product
""")

rows = old_cur.fetchall()
print(f"Productos encontrados: {len(rows)}\n")

insert_query = """
INSERT INTO core_inventory (code, name, category, stock, min_stock, unit, unit_price)
VALUES (?, ?, ?, ?, ?, ?, ?)
"""

for row in rows:
    code = row[0]
    name = row[1]
    category = row[2] or "Sin categoría"
    stock = row[3]
    min_stock = row[4]
    unit_price = row[5] or 0

    # unidad por defecto
    unit = "unidad"

    new_cur.execute(insert_query, (code, name, category, stock, min_stock, unit, unit_price))

new_conn.commit()

print("IMPORTACIÓN COMPLETA ✔")

old_conn.close()
new_conn.close()
