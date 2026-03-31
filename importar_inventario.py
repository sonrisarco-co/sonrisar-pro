import sqlite3

# Bases
OLD_DB = "db_old.sqlite3"
NEW_DB = "db.sqlite3"

print("Conectando bases de datos...")

old_conn = sqlite3.connect(OLD_DB)
old_cur = old_conn.cursor()

new_conn = sqlite3.connect(NEW_DB)
new_cur = new_conn.cursor()

print("IMPORTANDO INVENTARIO...\n")

# 1️⃣ Leer productos del sistema viejo
old_cur.execute("""
    SELECT id, nombre, descripcion, cantidad, buy_price, code, min_stock, provider
    FROM core_product
""")
productos = old_cur.fetchall()

print(f"Productos encontrados: {len(productos)}")

for p in productos:
    old_id, nombre, descripcion, cantidad, buy_price, code, min_stock, provider = p

    # 2️⃣ Revisar si hubo movimientos de stock
    old_cur.execute("""
        SELECT movement_type, quantity
        FROM core_stockmovement
        WHERE item_id = ?
    """, (old_id,))
    movimientos = old_cur.fetchall()

    stock_final = cantidad

    for mov_type, qty in movimientos:
        if mov_type == "in":
            stock_final += qty
        elif mov_type == "out":
            stock_final -= qty

    # 3️⃣ Insertar en la tabla CORRECTA del nuevo sistema: core_inventory
    new_cur.execute("""
        INSERT INTO core_inventory (name, code, category, stock, min_stock, unit, unit_price)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        nombre,
        code if code else "",
        descripcion if descripcion else "General",
        stock_final,
        min_stock,
        "unidad",
        buy_price if buy_price else 0
    ))

new_conn.commit()
old_conn.close()
new_conn.close()

print("\nIMPORTACIÓN DE INVENTARIO COMPLETA.")
