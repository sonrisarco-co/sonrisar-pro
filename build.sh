#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

if [ "$FORCE_CORE_RESTORE" = "1" ]; then
  echo "FORCE_CORE_RESTORE=1 -> cargando backup_core_final.json"
python manage.py loaddata backup_core_final_v2.json
else
  echo "Restore omitido"
fi

if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
  python manage.py createsuperuser --noinput || true
fi