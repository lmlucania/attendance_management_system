#!/bin/sh
python manage.py migrate
python manage.py collectstatic --noinput
if [ $DEBUG = 1 ]; then
    python manage.py runserver 0.0.0.0:8000
else
    gunicorn config.wsgi:application --bind 0.0.0.0:8000
fi