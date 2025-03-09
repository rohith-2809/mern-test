from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import google.generativeai as genai  # Updated client library

app = Flask(__name__)
CORS(app)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Retrieve your API key from the environment
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    logging.critical("GEMINI_API_KEY environment variable is not set.")
    raise ValueError("GEMINI_API_KEY environment variable is not set.")

# Configure the Google Generative AI client with your API key
genai.configure(api_key=API_KEY)

def get_cure_recommendation(plant_type, water_frequency, disease):
    """
    Generates a personalized plant care recommendation based on plant type,
    watering frequency, and disease name.
    """
    prompt = f"""
You are a compassionate and knowledgeable plant care advisor. Based on the details provided below, please generate a personalized plant care recommendation that is fresh and unique.

Plant Type: {plant_type}
Disease: {disease}
Watering Frequency: {water_frequency}

Instructions:
- If the disease indicates a problem (e.g., "magnesium toxicity"), begin with a gentle and empathetic tone.
- Provide 5 concise, numbered steps addressing the issue.
- Include specific care suggestions (such as appropriate fertilizers, remedies, or adjustments in watering routine) with online purchase links if possible.
- Keep the response engaging, concise, and no longer than 6 text lines.
- Ensure that the response is fresh and does not repeat phrases from previous answers.
Generate the personalized recommendation based on the above instructions.
    """
    prompt = prompt.strip()
    logging.debug("Generated prompt: %s", prompt)

    try:
        logging.info("Initializing Gemini Pro model for plantType: '%s', disease: '%s', water_frequency: '%s'", plant_type, disease, water_frequency)
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        logging.debug("Received response from Gemini: %s", response)
        if response.text:
            logging.info("Recommendation generated successfully.")
            return response.text.strip()
        else:
            logging.error("No text returned from the model for prompt: %s", prompt)
            return "No recommendation generated. Please try again later."
    except Exception as e:
        logging.exception("Error generating recommendation for prompt: %s", prompt)
        return f"An error occurred while generating the recommendation: {str(e)}"

@app.route('/recommend', methods=['POST'])
def gemini_recommendation():
    try:
        data = request.get_json()
        if not data:
            logging.error("Invalid JSON payload received.")
            return jsonify({'error': 'Invalid JSON payload'}), 400

        logging.debug("Received request data: %s", data)
        plant_type = data.get('plantType')
        water_frequency = data.get('waterFreq')
        disease = data.get('disease')

        missing_fields = []
        if not plant_type:
            missing_fields.append("plantType")
        if not water_frequency:
            missing_fields.append("waterFreq")
        if not disease:
            missing_fields.append("disease")
        if missing_fields:
            error_message = f"Missing required parameter(s): {', '.join(missing_fields)}"
            logging.error(error_message)
            return jsonify({'error': error_message}), 400

        recommendation = get_cure_recommendation(plant_type, water_frequency, disease)
        logging.debug("Final recommendation: %s", recommendation)
        return jsonify({'recommendation': recommendation})
    except Exception as e:
        logging.exception("Unexpected error in the /recommend endpoint.")
        return jsonify({'error': f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    # When deploying, ensure that the host and port settings align with your Render configuration.
    app.run(host='0.0.0.0', port=5001, debug=True)
