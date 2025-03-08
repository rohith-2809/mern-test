import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from googletrans import Translator

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

API_KEY = os.environ.get("GEMINI_API_KEY")
if API_KEY:
    logging.info("GEMINI_API_KEY is set.")
else:
    logging.warning("GEMINI_API_KEY is NOT set. Using fallback or may fail.")

# Configure the Generative AI library
genai.configure(api_key=API_KEY)

translator = Translator()

LANGUAGE_MAP = {
    "english": "en",
    "telugu": "te",
    "hindi": "hi",
}

def get_cure_recommendation(username, status, plant_type, water_frequency):
    greeting = f"Dear {username}," if username else ""
    prompt = f"""
{greeting}
You are a compassionate and knowledgeable plant care advisor...
(etc.)
    """
    try:
        # Use your numeric project ID in the model path:
        default_model = "projects/530092692805/locations/us-central1/models/text-bison-001"

        model_name = os.environ.get("GEMINI_MODEL_NAME", default_model)

        response = genai.generate_text(prompt=prompt, model=model_name)

        if response and response.text:
            return response.text.strip()
        else:
            logging.error("Generative AI did not return a valid text response.")
            return "The API did not return a valid response. Please try again later."
    except Exception as e:
        logging.exception("Error generating recommendation")
        return f"An error occurred while generating the recommendation: {str(e)}"

@app.route('/')
def index():
    return "Agent App is running. Use POST /recommend for recommendations."

@app.route('/recommend', methods=['POST'])
def gemini_recommendation():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON payload'}), 400

    username = data.get('username')
    status = data.get('status')
    plant_type = data.get('plantType')
    water_frequency = data.get('waterFreq')
    language = data.get('language', "english")

    # Validate fields
    missing_fields = []
    if not status:
        missing_fields.append("status")
    if not plant_type:
        missing_fields.append("plantType")
    if water_frequency is None:
        missing_fields.append("waterFreq")
    if missing_fields:
        return jsonify({'error': f"Missing parameter(s): {', '.join(missing_fields)}"}), 400

    # Generate recommendation
    recommendation = get_cure_recommendation(username, status, plant_type, water_frequency)

    # Optionally translate if not English
    if language.lower() != "english":
        dest_lang = LANGUAGE_MAP.get(language.lower(), "en")
        try:
            translated = translator.translate(recommendation, dest=dest_lang)
            recommendation = translated.text
        except Exception as e:
            logging.error(f"Translation error: {e}")
            recommendation += "\n\n(Note: Translation to your selected language failed.)"

    return jsonify({'recommendation': recommendation})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
