from flask import Flask, request, jsonify, render_template
from deep_translator import GoogleTranslator
from gtts import gTTS
import os
import tempfile
import base64
import speech_recognition as sr
from werkzeug.utils import secure_filename
import logging
import json
from datetime import datetime
from functools import lru_cache
import time
from pydub import AudioSegment
import imageio_ffmpeg
import io

app = Flask(__name__, template_folder='templates')
app.logger.setLevel(logging.DEBUG)

# Setup logging formatter
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Configure pydub to use bundled ffmpeg (via imageio-ffmpeg)
try:
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    AudioSegment.converter = ffmpeg_path
except Exception as e:
    # Log and proceed; conversion will be skipped if not available
    logging.warning(f"FFmpeg binary not found via imageio-ffmpeg: {e}")

# Configure upload folder
UPLOAD_FOLDER = '/tmp/audio_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Define language codes with auto-detect support
LANGUAGE_CODES = {
    "English": "en",
    "Hindi": "hi",
    "Bengali": "bn",
    "Spanish": "es",
    "Chinese (Simplified)": "zh-CN",
    "Russian": "ru",
    "Japanese": "ja",
    "Korean": "ko",
    "German": "de",
    "French": "fr",
    "Tamil": "ta",
    "Telugu": "te",
    "Kannada": "kn",
    "Gujarati": "gu",
    "Punjabi": "pa"
}

# TTS Cache: (text, lang) -> base64 audio
tts_cache = {}
MAX_CACHE_SIZE = 100

def get_temp_filepath(prefix='audio_', suffix='.wav'):
    """Generate a temporary file path."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    filename = f"{prefix}{timestamp}{suffix}"
    return os.path.join(app.config['UPLOAD_FOLDER'], filename)

def cleanup_old_files(max_age_seconds=3600):
    """Remove audio files older than max_age_seconds."""
    try:
        current_time = time.time()
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(filepath):
                file_age = current_time - os.path.getmtime(filepath)
                if file_age > max_age_seconds:
                    os.remove(filepath)
    except Exception as e:
        app.logger.warning(f"Error cleaning up old files: {e}")

def convert_audio_to_wav(audio_data, input_format):
    """Convert various audio formats to WAV for speech recognition."""
    try:
        # Try to load the audio
        audio = AudioSegment.from_file(io.BytesIO(audio_data), format=input_format.replace('audio/', '').split(';')[0])
        
        # Convert to WAV format (mono, 16kHz)
        wav_audio = audio.set_channels(1).set_frame_rate(16000)
        
        # Export to bytes
        wav_buffer = io.BytesIO()
        wav_audio.export(wav_buffer, format='wav')
        wav_buffer.seek(0)
        return wav_buffer.read()
    except Exception as e:
        app.logger.warning(f"Could not convert audio format: {e}. Attempting direct recognition...")
        return audio_data

def cache_tts(text, lang_code, audio_base64):
    """Cache TTS result with LRU eviction."""
    global tts_cache
    
    cache_key = (text[:100], lang_code)  # Limit key size
    
    if len(tts_cache) >= MAX_CACHE_SIZE:
        # Remove oldest entry (simple FIFO)
        tts_cache.pop(next(iter(tts_cache)))
    
    tts_cache[cache_key] = audio_base64

def get_cached_tts(text, lang_code):
    """Retrieve cached TTS audio."""
    cache_key = (text[:100], lang_code)
    return tts_cache.get(cache_key)

@app.route('/healthz', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html', languages=LANGUAGE_CODES.keys())

@app.route('/translate', methods=['POST'])
def translate():
    """Translate text from one language to another."""
    try:
        start_time = time.time()
        app.logger.info("Received translation request")
        
        data = request.json
        text = data.get('text', '').strip()
        from_lang_name = data.get('from_lang', 'English')
        to_lang_name = data.get('to_lang', 'Hindi')
        
        # Validate input
        if not text:
            return jsonify({
                'success': False,
                'error': 'No text provided for translation'
            }), 400
        
        if len(text) > 5000:
            return jsonify({
                'success': False,
                'error': 'Text is too long (max 5000 characters)'
            }), 400
        
        # Get language codes
        from_lang = LANGUAGE_CODES.get(from_lang_name, 'en') if from_lang_name != 'auto' else 'auto'
        to_lang = LANGUAGE_CODES.get(to_lang_name, 'en')
        
        app.logger.info(f"Translating from {from_lang} to {to_lang}: {text[:50]}...")
        
        # Translate text with retry logic
        translated_text = None
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                translator = GoogleTranslator(source=from_lang, target=to_lang)
                translated_text = translator.translate(text=text)
                break
            except Exception as e:
                app.logger.warning(f"Translation attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(1)  # Brief delay before retry
        
        if not translated_text:
            return jsonify({
                'success': False,
                'error': 'Translation produced empty result'
            }), 500
        
        app.logger.info(f"Translation successful: {translated_text[:50]}...")
        
        # Generate audio for translated text with cache check
        cached_audio = get_cached_tts(translated_text, to_lang)
        
        if cached_audio:
            app.logger.info("Using cached audio")
            audio_base64 = cached_audio
        else:
            app.logger.info("Generating new audio with gTTS")
            try:
                tts = gTTS(text=translated_text, lang=to_lang, slow=False)
                
                # Save to bytes buffer
                mp3_buffer = io.BytesIO()
                tts.write_to_fp(mp3_buffer)
                mp3_buffer.seek(0)
                
                audio_base64 = base64.b64encode(mp3_buffer.read()).decode('utf-8')
                
                # Cache the result
                cache_tts(translated_text, to_lang, audio_base64)
            except Exception as e:
                app.logger.warning(f"gTTS generation failed: {e}. Will still return translation.")
                audio_base64 = None
        
        elapsed = time.time() - start_time
        app.logger.info(f"Translation completed in {elapsed:.2f}s")
        
        return jsonify({
            'success': True,
            'translated_text': translated_text,
            'audio': audio_base64,
            'elapsed_seconds': round(elapsed, 2)
        })

    except Exception as e:
        app.logger.error(f"Translation error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Translation failed: {str(e)}'
        }), 500

@app.route('/speech-to-text', methods=['POST'])
def speech_to_text():
    """Convert speech from audio file to text."""
    try:
        start_time = time.time()
        app.logger.info("Received speech-to-text request")
        
        if 'audio' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No audio file provided'
            }), 400

        audio_file = request.files['audio']
        if not audio_file or audio_file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Empty audio file'
            }), 400

        # Get content type
        content_type = audio_file.content_type or 'audio/wav'
        app.logger.info(f"Audio format: {content_type}")
        
        # Save the uploaded file
        temp_path = get_temp_filepath(suffix=f'.{content_type.split("/")[-1].split(";")[0]}')
        temp_wav_path = None
        
        try:
            audio_file.save(temp_path)
            app.logger.info(f"Audio saved to {temp_path}")
            
            # Convert to WAV if needed
            if 'wav' not in content_type.lower() and 'webm' in content_type.lower() or 'ogg' in content_type.lower():
                app.logger.info("Converting audio to WAV format...")
                temp_wav_path = get_temp_filepath(suffix='.wav')
                
                with open(temp_path, 'rb') as f:
                    audio_data = f.read()
                
                wav_data = convert_audio_to_wav(audio_data, content_type)
                
                with open(temp_wav_path, 'wb') as f:
                    f.write(wav_data)
                
                processing_path = temp_wav_path
            else:
                processing_path = temp_path
            
            # Initialize recognizer
            recognizer = sr.Recognizer()
            
            # Process the audio file with retry logic
            text = None
            max_retries = 2
            
            for attempt in range(max_retries):
                try:
                    with sr.AudioFile(processing_path) as source:
                        audio_data = recognizer.record(source)
                        text = recognizer.recognize_google(audio_data)
                    break
                except sr.UnknownValueError:
                    return jsonify({
                        'success': False,
                        'error': 'Could not understand audio. Please speak clearly.'
                    }), 400
                except sr.RequestError as e:
                    app.logger.warning(f"Recognition attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(1)
            
            if not text:
                return jsonify({
                    'success': False,
                    'error': 'Could not transcribe audio'
                }), 400
            
            elapsed = time.time() - start_time
            app.logger.info(f"Speech-to-text completed in {elapsed:.2f}s: {text[:50]}...")
            
            return jsonify({
                'success': True,
                'text': text,
                'elapsed_seconds': round(elapsed, 2)
            })
            
        finally:
            # Clean up temporary files
            for filepath in [temp_path, temp_wav_path]:
                if filepath and os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except Exception as e:
                        app.logger.warning(f"Could not remove temp file {filepath}: {e}")
        
    except sr.RequestError as e:
        app.logger.error(f"Speech recognition service error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Speech recognition service error: {str(e)}'
        }), 503
    except Exception as e:
        app.logger.error(f"Speech-to-text error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Processing failed: {str(e)}'
        }), 500

@app.after_request
def after_request(response):
    """Add CORS headers."""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    response.headers.add('X-Content-Type-Options', 'nosniff')
    return response

@app.before_request
def before_request():
    """Cleanup old files before each request."""
    cleanup_old_files()

if __name__ == '__main__':
    app.run(debug=False)
