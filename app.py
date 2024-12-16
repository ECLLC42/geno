from flask import Flask, request, jsonify, render_template
import requests
from dotenv import load_dotenv
import os
from utils.lyric_generator import generate_lyrics as generate_lyrics_ai
from tasks.song_tasks import generate_song_task, SongGenerationError
from flask_socketio import SocketIO
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration from .env
API_URL = os.getenv("API_URL")
API_TOKEN = os.getenv("API_TOKEN")
ACCOUNT_ID = os.getenv("ACCOUNT_ID")

socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/hidden')
def hidden():
    return render_template('hidden.html')

@app.route('/verify', methods=['GET'])
def verify():
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_TOKEN}"
    }
    body = {
        "account": ACCOUNT_ID,
        "token": os.getenv("MUREKA_TOKEN")
    }

    response = requests.post(f"{API_URL}accounts/{ACCOUNT_ID}", headers=headers, json=body)

    if response.status_code == 201:
        return jsonify({"message": "Authentication successful", "data": response.json()}), 201
    elif response.status_code == 401:
        return jsonify({"error": "Authentication failed, unauthorized"}), 401
    else:
        return jsonify({"error": "An error occurred", "details": response.json()}), response.status_code

@app.route('/profile', methods=['GET'])
def profile():
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {API_TOKEN}"
    }
    
    api_url = f"https://api.useapi.net/v1/mureka/profile/?account={ACCOUNT_ID}"
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        return render_template('profile.html', data=response.json())
    elif response.status_code == 401:
        return jsonify({"error": "Unauthorized access"}), 401
    elif response.status_code == 400:
        return jsonify({"error": "Bad Request", "details": response.json()}), 400
    else:
        return jsonify({"error": "An error occurred", "details": response.json()}), response.status_code

@app.route('/create')
def create():
    return render_template('lyrics.html')

@app.route('/generate_lyrics', methods=['POST'])
def generate_lyrics_route():
    user_input = request.form.get('lyrics_input')
    generated_lyrics = generate_lyrics_ai(user_input)
    return render_template('music_styles.html', lyrics=generated_lyrics)

@app.route('/select_moods', methods=['POST'])
def select_moods():
    lyrics = request.form.get('lyrics')
    genres = request.form.getlist('genres[]')
    return render_template('moods.html', lyrics=lyrics, genres=genres)

@app.route('/select_vocals', methods=['POST'])
def select_vocals():
    lyrics = request.form.get('lyrics')
    genres = request.form.getlist('genres[]')
    moods = request.form.getlist('moods[]')
    return render_template('vocals.html', lyrics=lyrics, genres=genres, moods=moods)

@app.route('/listen', methods=['POST'])
def listen():
    try:
        lyrics = request.form.get('lyrics')
        genres = request.form.getlist('genres[]')
        moods = request.form.getlist('moods[]')
        vocals = request.form.get('vocals')
        
        # Enhanced logging
        logger.info("=== Starting Song Generation ===")
        logger.info(f"Lyrics (first 50 chars): {lyrics[:50]}...")
        logger.info(f"Selected Genres: {genres}")
        logger.info(f"Selected Moods: {moods}")
        logger.info(f"Selected Vocals: {vocals}")
        
        # Start the Celery task with vocals parameter
        task = generate_song_task.delay(lyrics, genres, moods, vocals)
        logger.info(f"Created Celery task with ID: {task.id}")
        
        return render_template('listen.html', 
                             lyrics=lyrics,
                             genres=genres,
                             moods=moods,
                             vocals=vocals,
                             task_id=task.id)
                             
    except Exception as e:
        logger.error(f"Error in listen route: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred"}), 500

@app.route('/task_status/<task_id>')
def task_status(task_id):
    try:
        task = generate_song_task.AsyncResult(task_id)
        logger.info(f"Task state: {task.state}")
        logger.info(f"Task info: {task.info}")
        
        if task.state == 'PENDING':
            response = {
                'state': task.state,
                'status': 'Task is pending...'
            }
        elif task.state == 'FAILURE':
            response = {
                'state': task.state,
                'status': str(task.info.get('error', 'An error occurred'))
            }
        else:
            response = {
                'state': task.state,
                'status': task.info.get('status', ''),
                'song_data': task.info.get('song_data', {})
            }
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error checking task status: {str(e)}")
        return jsonify({
            'state': 'ERROR',
            'status': 'Error checking task status'
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
