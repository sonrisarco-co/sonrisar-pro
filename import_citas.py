import sqlite3
import os

# Archivos
OLD_DB = "db_prueba.sqlite3"   # base vieja
NEW_DB = "db.sqlite3"          # base nueva (productiva)

# 1. Verificar que la base vieja existe
if not os.path.exists(OLD_DB):
    print("ERROR: No se encontró", OLD_DB)
    exit()

print("Conectando a bases de datos...")
old_conn = sqlite3.connect(OLD_DB)
new_conn = sqlite3.connect(NEW_DB)

old_cur = old_conn.cursor()
new_cur = new_conn.cursor()

print("IMPORTANDO CITAS...")

# 2. Leer citas desde la base vieja
old_cur.execute("""
    SELECT id, fecha, hora, motivo, estado, paciente_id, observaciones
    FROM core_appointment
""")
rows = old_cur.fetchall()

# 3. Insertar en la base nueva
for r in rows:
    id_old, fecha, hora, motivo, estado, paciente_id, observaciones = r

    # insertar directamente
    new_cur.execute("""
        INSERT INTO core_appointment (fecha, hora, motivo, estado, paciente_id, observaciones)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (fecha, hora, motivo, estado, paciente_id, observaciones))

new_conn.commit()

print(f"LISTO ✔ Se importaron {len(rows)} citas correctamente.")

old_conn.close()
new_conn.close()