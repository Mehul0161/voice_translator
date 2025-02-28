from flask import Flask, request, jsonify, render_template
from deep_translator import GoogleTranslator
from gtts import gTTS
import os
import tempfile
import base64
import speech_recognition as sr

app = Flask(__name__)

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
        data = request.json
        text = data.get('text')
        from_lang = LANGUAGE_CODES[data.get('from_lang')]
        to_lang = LANGUAGE_CODES[data.get('to_lang')]

        # Translate text
        translator = GoogleTranslator(source=from_lang, target=to_lang)
        translated_text = translator.translate(text=text)

        # Generate audio for translated text
        tts = gTTS(text=translated_text, lang=to_lang)
        
        # Save audio to temporary file and convert to base64
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
            tts.save(fp.name)
            with open(fp.name, 'rb') as audio_file:
                audio_base64 = base64.b64encode(audio_file.read()).decode('utf-8')
            os.unlink(fp.name)

        return jsonify({
            'success': True,
            'translated_text': translated_text,
            'audio': audio_base64
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/speech-to-text', methods=['POST'])
def speech_to_text():
    try:
        audio_file = request.files['audio']
        recognizer = sr.Recognizer()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as fp:
            audio_file.save(fp.name)
            with sr.AudioFile(fp.name) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data)
            os.unlink(fp.name)
            
        return jsonify({
            'success': True,
            'text': text
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True) 