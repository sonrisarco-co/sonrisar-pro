#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --fake-initial --noinput
python manage.py loaddata backup_total.json --exclude contenttypes --exclude auth.permission --exclude admin.logentry --exclude sessions || true


if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
  python manage.py createsuperuser --noinput || true
fi