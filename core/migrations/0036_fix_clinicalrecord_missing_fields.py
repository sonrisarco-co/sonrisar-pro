from django.db import migrations


def add_column_if_missing(schema_editor, table, column_sql):
    cursor = schema_editor.connection.cursor()
    column_name = column_sql.split()[0]

    existing_columns = [
        col.name for col in schema_editor.connection.introspection.get_table_description(cursor, table)
    ]

    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_sql}")


def forwards(apps, schema_editor):
    table = "core_clinicalrecord"

    columns = [
        "diabetes boolean NOT NULL DEFAULT 0",
        "hta boolean NOT NULL DEFAULT 0",
        "cardiopatia boolean NOT NULL DEFAULT 0",
        "ninguno boolean NOT NULL DEFAULT 0",
        "otros_antecedentes varchar(200) NOT NULL DEFAULT ''",
        "medicacion_actual text NOT NULL DEFAULT ''",
        "alergias text NOT NULL DEFAULT ''",
        "cirugias_previas text NOT NULL DEFAULT ''",
        "pronostico varchar(10) NOT NULL DEFAULT ''",
        "consentimiento_explicado boolean NOT NULL DEFAULT 0",
        "consentimiento_aceptado boolean NOT NULL DEFAULT 0",
        "consentimiento_firma boolean NOT NULL DEFAULT 0",
    ]

    for column_sql in columns:
        add_column_if_missing(schema_editor, table, column_sql)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0035_clinicalrecord_alergias_clinicalrecord_cardiopatia_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]