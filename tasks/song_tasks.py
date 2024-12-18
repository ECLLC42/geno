from .celery_config import celery
import requests
import os
from dotenv import load_dotenv
import json
from utils.s3_handler import S3Handler, S3Error, S3DownloadError, S3UploadError
import logging
from datetime import datetime
from utils.song_generator import generate_song
from celery import current_task

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SongGenerationError(Exception):
    """Custom exception for song generation errors"""
    pass

@celery.task(bind=True)
def generate_song_task(self, lyrics, genres, moods, vocals, instruments):
    logger.info("=== Starting Song Generation ===")
    logger.info(f"Received lyrics: {lyrics}")
    logger.info(f"Lyrics type: {type(lyrics)}")
    result = generate_song(lyrics, genres, moods, vocals, instruments)
    logger.info(f"Song generation successful: {result}")
    return result