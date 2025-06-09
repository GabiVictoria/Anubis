release: python manage.py collectstatic --no-input
web: python manage.py migrate && gunicorn anubis.wsgi