#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

python manage.py shell -c "from core.models import Patient; import sys; sys.exit(0 if Patient.objects.exists() else 1)" \
  && echo 'Base con datos, se omite loaddata' \
  || python manage.py loaddata backup_final.json

python manage.py createsuperuser --noinput || true