web: gunicorn app:app
worker: celery -A tasks.song_tasks worker --loglevel=info