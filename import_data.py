import sqlite3
import os

# ---------------------------------------
# CONFIGURAR NOMBRES DE ARCHIVOS
# ---------------------------------------
OLD_DB = "db_old.sqlite3"     # Base de datos vieja (odontosoft)
NEW_DB = "db.sqlite3"         # Base de datos nueva (sonrisarpro)

if not os.path.exists(OLD_DB):
    print("❌ ERROR: No se encontró", OLD_DB)
    exit()

print("Conectando base vieja y nueva...")

old_conn = sqlite3.connect(OLD_DB)
new_conn = sqlite3.connect(NEW_DB)

old_cur = old_conn.cursor()
new_cur = new_conn.cursor()

print("\n==============================")
print("IMPORTANDO PACIENTES...")
print("==============================\n")

# ---------------------------------------
# LEER PACIENTES DESDE BASE VIEJA
# ---------------------------------------
try:
    old_cur.execute("""
        SELECT 
            first_name, 
            last_name, 
            document, 
            phone, 
            email, 
            notes
        FROM core_patient
    """)
    rows = old_cur.fetchall()

except Exception as e:
    print("❌ ERROR al leer core_patient:", e)
    exit()

insertados = 0

for r in rows:
    first, last, document, phone, email, notes = r

    # Evitar nulos
    if document is None:
        continue

    # ---------------------------------------
    # Verificar si existe paciente con esa CI
    # ---------------------------------------
    new_cur.execute("SELECT id FROM core_patient WHERE ci = ?", (document,))
    existe = new_cur.fetchone()

    if existe:
        print(f"🔵 Ya existe paciente con CI {document}, se omite.")
        continue

    # ---------------------------------------
    # Insertar en nueva base
    # ---------------------------------------
    new_cur.execute("""
        INSERT INTO core_patient (nombre, apellido, ci, telefono, email, direccion)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (first, last, document, phone, email, notes))

    insertados += 1

new_conn.commit()

print(f"\n✅ Pacientes importados correctamente: {insertados}")
print("🚀 Listo.\n")

old_conn.close()
new_conn.close()
