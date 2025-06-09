release: python manage.py collectstatic --no-input && python manage.py migrate
web: gunicorn anubis.wsgi
