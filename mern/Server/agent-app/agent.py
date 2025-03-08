import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from googletrans import Translator

app = Flask(__name__)
CORS(app)

# Set logging to INFO level to see our debug messages
logging.basicConfig(level=logging.INFO)

# 1. Retrieve your API key from Render's environment variables
API_KEY = os.environ.get("GEMINI_API_KEY")

# 2. Log whether the key is present (avoid printing the entire key)
if API_KEY:
    logging.info("GEMINI_API_KEY is set.")
else:
    logging.warning("GEMINI_API_KEY is NOT set. Using fallback or may fail.")

# 3. Configure google.generativeai with the retrieved key
genai.configure(api_key=API_KEY)

translator = Translator()

LANGUAGE_MAP = {
    "english": "en",
    "telugu": "te",
    "hindi": "hi",
    # Add more languages if needed
}

def get_cure_recommendation(username, status, plant_type, water_frequency):
    """
    Generate a plant-care recommendation using the generative AI model.
    """
    greeting = f"Dear {username}," if username else ""
    prompt = f"""
{greeting}
You are a compassionate and knowledgeable plant care advisor. Based on the details provided below, please generate a personalized plant care recommendation that is completely fresh and unique each time.

If the plant appears healthy:
- Begin with a cheerful greeting.
- Include a **new, never-repeated fun fact** about caring for a {plant_type}.
- Recommend a maintenance fertilizer and include an online purchase link if possible.
- Use upbeat language with plant-related emojis (e.g., 🌿, 🌸, 🍃).

If the plant shows signs of disease or abnormality (for example, 'Guava_Dot', yellow leaves, spots, or drooping):
- Begin with a gentle, empathetic concern using caution emojis (⚠️🚨).
- Provide **5 concise, numbered steps** focusing on recovery and improved care.
- Recommend at least **two specific fertilizers** (include brand names if possible) with direct online purchase links if available.
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
    try:
        # Use a supported model name.
        # This will use the value of GEMINI_MODEL_NAME if set, or default to "text-bison-001"
        model_name = os.environ.get("GEMINI_MODEL_NAME", "text-bison-001")

        # Call the updated generate_text method
        response = genai.generate_text(prompt=prompt, model=model_name)

        # Check the response for valid text
        if response and response.text:
            return response.text.strip()
        else:
            logging.error("Generative AI did not return a valid text response.")
            return "The API did not return a valid response. Please try again later."
    except Exception as e:
        logging.exception("Error generating recommendation")
        return f"An error occurred while generating the recommendation: {str(e)}"

# ---------------------------------------------------------
# ROOT ROUTE (HEALTH CHECK)
@app.route('/')
def index():
    return "Agent App is running. Use POST /recommend for recommendations."
# ---------------------------------------------------------

@app.route('/recommend', methods=['POST'])
def gemini_recommendation():
    """
    Receives a JSON payload with:
    {
        "username": <string, optional>,
        "status": <string>,
        "plantType": <string>,
        "waterFreq": <int>,
        "language": <string, optional>
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON payload'}), 400

    username = data.get('username')
    status = data.get('status')
    plant_type = data.get('plantType')
    water_frequency = data.get('waterFreq')
    language = data.get('language', "english")

    # Check for missing fields
    missing_fields = []
    if not status:
        missing_fields.append("status")
    if not plant_type:
        missing_fields.append("plantType")
    if water_frequency is None:
        missing_fields.append("waterFreq")

    if missing_fields:
        return jsonify({
            'error': f"Missing required parameter(s): {', '.join(missing_fields)}"
        }), 400

    # Generate recommendation
    recommendation = get_cure_recommendation(username, status, plant_type, water_frequency)

    # If language is not English, attempt translation
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
    # If you're deploying on Render, it will set PORT automatically.
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
