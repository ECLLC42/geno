import os
import requests
import json
import logging
from utils.s3_handler import S3Handler

logger = logging.getLogger(__name__)

class SongGenerationError(Exception):
    pass

def generate_song(lyrics, genres, moods, vocals, instruments):
    try:
        # Log the incoming lyrics
        logger.info(f"Preparing to send lyrics to Mureka API: {lyrics[:100]}...")
        
        api_url = "https://api.useapi.net/v1/mureka/music/create-advanced"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('API_TOKEN')}"
        }
        
        # Combine genres, moods, instruments, vocals for the desc parameter
        # The desc parameter should be a comma-separated string of musical attributes
        desc_elements = []
        if genres:
            desc_elements.extend(genres)
        if moods:
            desc_elements.extend(moods)
        if instruments:
            desc_elements.extend(instruments)
        if vocals:
            desc_elements.append(vocals)
            
        # Create the final desc string
        desc = ", ".join(desc_elements)
        
        # Log the request parameters for debugging
        logger.info(f"Sending request with lyrics: {lyrics}")
        logger.info(f"Description parameter: {desc}")
        
        body = {
            "account": os.getenv('ACCOUNT_ID'),
            "lyrics": lyrics,
            "desc": desc
        }
        
        response = requests.post(api_url, headers=headers, json=body)
        
        if response.status_code == 200:
            data = response.json()
            if not data.get('songs'):
                raise SongGenerationError("No songs were generated")
            
            # Get the last song (most refined version)
            song = data['songs'][-1]
            
            # Initialize S3 handler and process URLs
            s3_handler = S3Handler()
            try:
                urls = s3_handler.download_and_upload_to_s3(
                    song['mp3_url'],
                    song['song_id']
                )
                # Update URLs in response
                song['mp3_url'] = urls['play_url']
                song['download_url'] = urls['download_url']
            except Exception as e:
                logger.error(f"S3 operation failed: {str(e)}")
                song['download_url'] = song['mp3_url']
            
            return {'songs': [song]}
            
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