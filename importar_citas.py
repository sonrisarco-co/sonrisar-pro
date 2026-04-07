import sqlite3
from datetime import datetime

# Conectar bases
old_db = 'db_old.sqlite3'
new_db = 'db.sqlite3'

old_conn = sqlite3.connect(old_db)
old_cur = old_conn.cursor()

new_conn = sqlite3.connect(new_db)
new_cur = new_conn.cursor()

print("IMPORTANDO CITAS...")

# Leer datos de la base vieja
rows = old_cur.execute("""
    SELECT id, start_ts, type, status, notes, patient_id
    FROM core_appointment
""").fetchall()

for r in rows:
    old_id, start_ts, tipo, estado, notas, paciente_id = r

    # Separar fecha y hora desde start_ts
    try:
        dt = datetime.fromisoformat(start_ts)
        fecha = dt.date().isoformat()
        hora = dt.time().isoformat(timespec='minutes')
    except:
        fecha = None
        hora = None

    # Insertar en nueva base
    new_cur.execute("""
        INSERT INTO core_appointment (fecha, hora, motivo, estado, observaciones, paciente_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (fecha, hora, tipo, estado, notas, paciente_id))

new_conn.commit()

print("CITAS IMPORTADAS CON ÉXITO.")

old_conn.close()
new_conn.close()
