#!/usr/bin/env bash

pip install -r requirements.txt

python manage.py migrate --fake

python manage.py collectstatic --noinput