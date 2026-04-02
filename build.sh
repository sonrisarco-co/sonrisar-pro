#!/usr/bin/env bash
set -e

echo "=== INSTALANDO ==="
pip install -r requirements.txt

echo "=== MIGRANDO ==="
python manage.py migrate

echo "=== CARGANDO DATOS ==="
python manage.py loaddata datos.json

echo "=== STATIC ==="
python manage.py collectstatic --noinput

echo "=== FIN BUILD ==="