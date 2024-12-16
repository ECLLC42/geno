from .celery_config import celery
import requests
import os
from dotenv import load_dotenv
import json
from utils.s3_handler import S3Handler, S3Error, S3DownloadError, S3UploadError
import logging
from datetime import datetime

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SongGenerationError(Exception):
    """Custom exception for song generation errors"""
    pass

@celery.task(bind=True)
def generate_song_task(self, lyrics, genres, moods):
    task_id = self.request.id
    logger.info(f"Starting song generation task {task_id}")
    logger.info(f"Input - Lyrics: {lyrics[:50]}..., Genres: {genres}, Moods: {moods}")
    
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
            
        desc = ", ".join(genres + moods)
        logger.info(f"Description for API: {desc}")
        
        body = {
            "account": os.getenv('ACCOUNT_ID'),
            "lyrics": lyrics,
            "desc": desc
        }
        
        # Log API request
        logger.info(f"Making API request to Mureka with body length: {len(str(body))}")
        self.update_state(state='PROGRESS', meta={
            'status': '🎵 Geno is composing your special song! 🎵',
            'timestamp': datetime.now().isoformat()
        })
        
        response = requests.post(api_url, headers=headers, json=body)
        logger.info(f"API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"API Response: {str(data)[:200]}...")  # Log first 200 chars
            
            if not data.get('songs'):
                logger.error("No songs in API response")
                raise SongGenerationError("No songs were generated")
            
            logger.info(f"Number of songs generated: {len(data['songs'])}")
            
            s3_handler = S3Handler()
            self.update_state(state='PROGRESS', meta={
                'status': '🌟 Adding the final sprinkle of magic! 🌟',
                'songs_count': len(data['songs']),
                'timestamp': datetime.now().isoformat()
            })
            
            # Track S3 upload success/failure
            s3_success = 0
            s3_failures = 0
            
            for idx, song in enumerate(data['songs']):
                try:
                    logger.info(f"Processing song {idx + 1}/{len(data['songs'])}")
                    logger.info(f"Original URL: {song['mp3_url']}")
                    
                    s3_url = s3_handler.download_and_upload_to_s3(
                        song['mp3_url'],
                        song['song_id']
                    )
                    song['mp3_url'] = s3_url['play_url']
                    song['download_url'] = s3_url['download_url']
                    s3_success += 1
                    logger.info(f"S3 upload successful. New URL: {s3_url}")
                    
                except (S3DownloadError, S3UploadError, S3Error) as e:
                    s3_failures += 1
                    logger.error(f"S3 operation failed for song {idx + 1}: {str(e)}")
                    logger.info("Keeping original URL")
            
            logger.info(f"S3 Operations Complete - Success: {s3_success}, Failures: {s3_failures}")
            
            self.update_state(state='SUCCESS', meta={
                'status': '🎉 Your magical song is ready! 🎉',
                'song_data': data,
                's3_success': s3_success,
                's3_failures': s3_failures,
                'timestamp': datetime.now().isoformat()
            })
            
            return data
            
        else:
            error_response = response.text
            logger.error(f"API Error - Status: {response.status_code}, Response: {error_response}")
            if response.status_code == 401:
                raise SongGenerationError("Authentication failed. Please check your API token.")
            elif response.status_code == 400:
                error_msg = response.json().get('error', 'Bad request')
                raise SongGenerationError(f"API Error: {error_msg}")
            else:
                raise SongGenerationError(f"Unexpected error: HTTP {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network Error: {str(e)}")
        self.update_state(state='FAILURE', meta={
            'status': 'Network error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        raise SongGenerationError(f"Network error: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON Decode Error: {str(e)}")
        self.update_state(state='FAILURE', meta={
            'status': 'Invalid API response',
            'error': 'Invalid JSON',
            'timestamp': datetime.now().isoformat()
        })
        raise SongGenerationError("Invalid response from API")
    except Exception as e:
        logger.error(f"Unexpected Error: {str(e)}", exc_info=True)
        self.update_state(state='FAILURE', meta={
            'status': 'Task failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        raise SongGenerationError(f"Failed to generate song: {str(e)}") 