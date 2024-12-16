import requests
import os
from dotenv import load_dotenv
import json
from utils.s3_handler import S3Handler, S3Error, S3DownloadError, S3UploadError
import logging
import time

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a file handler for ref_input.log
ref_handler = logging.FileHandler('ref_input.log')
ref_handler.setLevel(logging.INFO)
ref_formatter = logging.Formatter('%(asctime)s - %(message)s')
ref_handler.setFormatter(ref_formatter)
logger.addHandler(ref_handler)

class SongGenerationError(Exception):
    """Custom exception for song generation errors"""
    pass

# When generating the MP3, we should use these high quality settings:
AUDIO_SETTINGS = {
    'bitrate': '320k',  # Highest MP3 bitrate
    'sample_rate': 44100,  # CD quality sample rate
    'channels': 2,  # Stereo
    'format': 'mp3',
    'codec': 'libmp3lame',
    'quality': 0  # Highest quality setting for LAME encoder
}

def generate_song(lyrics, genres, moods, vocals, instruments):
    try:
        api_url = "https://api.useapi.net/v1/mureka/music/create-advanced"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('API_TOKEN')}"
        }
        
        # Validate inputs
        if not lyrics:
            raise SongGenerationError("Lyrics are required")
        if not genres and not moods:
            raise SongGenerationError("At least one genre or mood is required")
        if not vocals:
            raise SongGenerationError("Vocal type is required")
            
        # Combine genres, moods, instruments, vocals, and fade for the desc parameter
        desc_elements = genres + moods + instruments + [vocals + ", fade to end"]
        desc = ", ".join(desc_elements)
        
        # Log the description parameter
        logger.info(f"Description parameter sent to API: {desc}")
        
        body = {
            "account": os.getenv('ACCOUNT_ID'),
            "lyrics": lyrics,
            "desc": desc  # vocals and fade to end are part of the description
        }
        
        response = requests.post(api_url, headers=headers, json=body)
        
        if response.status_code == 200:
            data = response.json()
            if not data.get('songs'):
                raise SongGenerationError("No songs were generated")
            
            # Initialize S3 handler
            s3_handler = S3Handler()
            
            # Upload each song to S3 and update the URLs
            for song in data['songs']:
                try:
                    urls = s3_handler.download_and_upload_to_s3(
                        song['mp3_url'],
                        song['song_id']
                    )
                    # Update both URLs
                    song['mp3_url'] = urls['play_url']
                    song['download_url'] = urls['download_url']
                except Exception as e:
                    logger.error(f"S3 operation failed: {str(e)}")
                    # Keep original URL for both
                    song['download_url'] = song['mp3_url']
            
            return data
        elif response.status_code == 401:
            raise SongGenerationError("Authentication failed. Please check your API token.")
        elif response.status_code == 400:
            error_msg = response.json().get('error', 'Bad request')
            raise SongGenerationError(f"API Error: {error_msg}")
        else:
            raise SongGenerationError(f"Unexpected error: HTTP {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        raise SongGenerationError(f"Network error: {str(e)}")
    except json.JSONDecodeError:
        raise SongGenerationError("Invalid response from API")
    except Exception as e:
        raise SongGenerationError(f"Unexpected error: {str(e)}") 