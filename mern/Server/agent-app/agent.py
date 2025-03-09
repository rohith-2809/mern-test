from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
from googletrans import Translator
import google.generativeai as genai  # Updated client library

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# Retrieve your API key from the environment
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set.")

# Configure the Google Generative AI client with your API key
genai.configure(api_key=API_KEY)

# Initialize the translator and language mappings
translator = Translator()
LANGUAGE_MAP = {
    "english": "en",
    "telugu": "te",
    "hindi": "hi",
    # add more mappings as needed
}

def get_cure_recommendation(username, status, plant_type, water_frequency):
    """
    Generates a fresh, personalized plant care recommendation using the Gemini Pro model.
    """
    greeting = f"Dear {username}," if username else ""
    # Build the prompt for generating a recommendation
    prompt = f"""
{greeting}
You are a compassionate and knowledgeable plant care advisor. Based on the details provided below, please generate a personalized plant care recommendation that is completely fresh and unique each time.

If the plant appears healthy:
- Begin with a cheerful greeting.
- Include a new, never-repeated fun fact about caring for a {plant_type}.
- Recommend a maintenance fertilizer and include an online purchase link if possible.
- Use upbeat language with plant-related emojis (e.g., 🌿, 🌸, 🍃).

If the plant shows signs of disease or abnormality (for example, 'Guava_Dot', yellow leaves, spots, or drooping):
- Begin with a gentle, empathetic concern using caution emojis (⚠️🚨).
- Provide 5 concise, numbered steps focusing on recovery and improved care.
- Recommend at least two specific fertilizers (include brand names if possible) with direct online purchase links if available.
- Suggest natural remedies or adjustments in the care routine.
- Ensure the recovery advice is new and uniquely generated.

---------------------------
User-Provided Details:
- Plant Status: {status}
- Plant Type: {plant_type}
- Watering Frequency: Every {water_frequency} days

Additional Instructions:
- Always generate a fresh and unique recommendation that feels new each time.
- Avoid repeating phrases or identical wording from previous responses.
- Keep the response engaging, concise, and no longer than 6 text lines.
- Include fertilizer suggestions with online links where possible.
---------------------------

Generate the personalized, engaging recommendation based on the above instructions.
    """
    prompt = prompt.strip()

    try:
        # Use the updated Gemini Pro model with the new client method
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt, temperature=0.7, candidate_count=1)
        if response.text:
            return response.text.strip()
        else:
            logging.error("No text returned from the model.")
            return "No recommendation generated. Please try again later."
    except Exception as e:
        logging.exception("Error generating recommendation")
        return f"An error occurred while generating the recommendation: {str(e)}"

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

    missing_fields = []
    if not status:
        missing_fields.append("status")
    if not plant_type:
        missing_fields.append("plantType")
    if not water_frequency:
        missing_fields.append("waterFreq")
    if missing_fields:
        return jsonify({'error': f"Missing required parameter(s): {', '.join(missing_fields)}"}), 400

    recommendation = get_cure_recommendation(username, status, plant_type, water_frequency)

    # Translate recommendation if needed
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
    app.run(host='0.0.0.0', port=5001, debug=True)
