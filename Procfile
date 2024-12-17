web: gunicorn app:app
worker: celery -A tasks.celery_config.celery worker --loglevel=info