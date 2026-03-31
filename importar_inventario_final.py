import sqlite3

old_db = "db_old.sqlite3"
new_db = "db.sqlite3"

old_conn = sqlite3.connect(old_db)
new_conn = sqlite3.connect(new_db)

old_cur = old_conn.cursor()
new_cur = new_conn.cursor()

print("Conectando a bases de datos...")
print("IMPORTANDO INVENTARIO...\n")

# Ahora usamos exactamente los nombres de columnas reales de core_product
old_cur.execute("""
SELECT 
    code,        -- código
    nombre,      -- nombre del producto
    cantidad,    -- stock actual
    min_stock,   -- stock mínimo
    buy_price,   -- precio unitario
    provider     -- proveedor
FROM core_product
""")

rows = old_cur.fetchall()
print(f"Productos encontrados: {len(rows)}")

for row in rows:
    codigo, nombre, cantidad, min_stock, precio, proveedor = row

    new_cur.execute("""
        INSERT INTO core_inventory (codigo, nombre, cantidad, stock_bajo, precio, proveedor)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (codigo, nombre, cantidad, min_stock, precio, proveedor))

new_conn.commit()

print("\nIMPORTACIÓN FINALIZADA ✔")

old_conn.close()
new_conn.close()
