from flask import Flask, request, jsonify, render_template, send_file
from deep_translator import GoogleTranslator
from gtts import gTTS
import os
import tempfile
import base64
import speech_recognition as sr
from werkzeug.utils import secure_filename
import logging

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

# Configure upload folder
UPLOAD_FOLDER = '/tmp/audio_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Define language codes
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

@app.route('/')
def index():
    return render_template('index.html', languages=LANGUAGE_CODES.keys())

@app.route('/translate', methods=['POST'])
def translate():
    try:
        app.logger.info("Received translation request")
        data = request.json
        text = data.get('text')
        from_lang = LANGUAGE_CODES[data.get('from_lang')]
        to_lang = LANGUAGE_CODES[data.get('to_lang')]

        app.logger.info(f"Translating from {from_lang} to {to_lang}: {text}")

        # Translate text
        translator = GoogleTranslator(source=from_lang, target=to_lang)
        translated_text = translator.translate(text=text)

        app.logger.info(f"Translated text: {translated_text}")

        # Generate audio for translated text
        tts = gTTS(text=translated_text, lang=to_lang)
        
        # Save audio to temporary file and convert to base64
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, 'output.mp3')
        
        try:
            tts.save(temp_path)
            with open(temp_path, 'rb') as audio_file:
                audio_base64 = base64.b64encode(audio_file.read()).decode('utf-8')
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)

        return jsonify({
            'success': True,
            'translated_text': translated_text,
            'audio': audio_base64
        })

    except Exception as e:
        app.logger.error(f"Translation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/speech-to-text', methods=['POST'])
def speech_to_text():
    try:
        app.logger.info("Received speech-to-text request")
        
        if 'audio' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No audio file provided'
            }), 400

        audio_file = request.files['audio']
        if not audio_file:
            return jsonify({
                'success': False,
                'error': 'Empty audio file'
            }), 400

        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, secure_filename('input.wav'))
        
        try:
            # Save the uploaded file
            audio_file.save(temp_path)
            
            # Initialize recognizer
            recognizer = sr.Recognizer()
            
            # Process the audio file
            with sr.AudioFile(temp_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data)
                
            return jsonify({
                'success': True,
                'text': text
            })
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        
    except sr.UnknownValueError:
        return jsonify({
            'success': False,
            'error': 'Could not understand audio'
        }), 400
    except sr.RequestError as e:
        return jsonify({
            'success': False,
            'error': f'Error with the speech recognition service: {str(e)}'
        }), 500
    except Exception as e:
        app.logger.error(f"Speech-to-text error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST')
    return response

if __name__ == '__main__':
    app.run(debug=True) 