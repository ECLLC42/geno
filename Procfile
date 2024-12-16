web: gunicorn app:app
worker: celery -A utils.celery_config.celery worker --loglevel=info