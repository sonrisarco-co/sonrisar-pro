import sqlite3

db = "db.sqlite3"
conn = sqlite3.connect(db)
cur = conn.cursor()

print("Normalizando motivos...")

# Traducir motivos
cur.execute("""
    UPDATE core_appointment
    SET motivo = 
        CASE 
            WHEN motivo = 'ortho' THEN 'Ortodoncia'
            WHEN motivo = 'other' THEN 'Otros'
            ELSE motivo
        END
""")

print("Normalizando estados...")

# Traducir estados
cur.execute("""
    UPDATE core_appointment
    SET estado =
        CASE
            WHEN estado = 'scheduled' THEN 'Programada'
            WHEN estado = 'cancelled' THEN 'Cancelada'
            WHEN estado = 'done' THEN 'Realizada'
            ELSE estado
        END
""")

conn.commit()
conn.close()

print("¡Listo! Motivos y estados están traducidos correctamente.")