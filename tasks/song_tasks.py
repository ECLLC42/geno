from .celery_config import celery
import requests
import os
from dotenv import load_dotenv
import json
from utils.s3_handler import S3Handler, S3Error, S3DownloadError, S3UploadError
import logging
from datetime import datetime
from utils.song_generator import generate_song

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SongGenerationError(Exception):
    """Custom exception for song generation errors"""
    pass

@celery.task(bind=True)
def generate_song_task(self, lyrics, genres, moods, vocals):
    task_id = self.request.id
    logger.info(f"Starting song generation task {task_id}")
    logger.info(f"Input - Lyrics: {lyrics[:50]}..., Genres: {genres}, Moods: {moods}, Vocals: {vocals}")
    
    try:
        api_url = "https://api.useapi.net/v1/mureka/music/create-advanced"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('API_TOKEN')}"
        }
        
        # Log API configuration
        logger.info(f"API URL: {api_url}")
        logger.info(f"Using Account ID: {os.getenv('ACCOUNT_ID')}")
        
        self.update_state(state='PROGRESS', meta={
            'status': '✨ Getting ready for some musical magic! ✨',
            'task_id': task_id,
            'timestamp': datetime.now().isoformat()
        })
        
        # Validate inputs with logging
        if not lyrics:
            logger.error("Lyrics validation failed: Empty lyrics")
            raise SongGenerationError("Lyrics are required")
        if not genres and not moods:
            logger.error("Genre/Mood validation failed: No genres or moods provided")
            raise SongGenerationError("At least one genre or mood is required")
        if not vocals:
            logger.error("Vocals validation failed: No vocal type selected")
            raise SongGenerationError("Vocal type is required")
            
        # Call the generate_song function with all parameters
        result = generate_song(lyrics, genres, moods, vocals)
        
        self.update_state(state='SUCCESS', meta={
            'status': '🎉 Your magical song is ready! 🎉',
            'song_data': result,
            'timestamp': datetime.now().isoformat()
        })
        
        return result
            
    except Exception as e:
        logger.error(f"Task failed: {str(e)}", exc_info=True)
        self.update_state(state='FAILURE', meta={
            'status': 'Task failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        raise 