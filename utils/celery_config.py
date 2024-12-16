from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

def make_celery(app=None):
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    celery = Celery(
        'tasks',
        broker=REDIS_URL,
        backend=REDIS_URL,
        include=['tasks.song_tasks']
    )
    
    celery.conf.update(
        broker_url=REDIS_URL,
        result_backend=REDIS_URL,
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        result_expires=3600,
        broker_connection_retry_on_startup=True,
        broker_connection_max_retries=None,
    )
    
    return celery

celery = make_celery() 