import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"  # Disable GPU

import logging
import traceback
import io
import tempfile
import re
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageOps  # For image processing

# Import gradio_client to call the remote Hugging Face Spaces APIs
from gradio_client import Client, handle_file

app = Flask(__name__)
CORS(app, supports_credentials=True)
logging.basicConfig(level=logging.INFO)

# Instantiate Gradio API clients from your Hugging Face Spaces
binary_client = Client("vittamraj/predict-binary-api")
multi_client = Client("vittamraj/predict-MultiClass-api")

# Define a healthy threshold (adjust as needed)
HEALTHY_THRESHOLD = 0.5

def dynamic_crop(img):
    """
    Dynamically crop the image by converting to grayscale, inverting it,
    thresholding, and cropping to the detected bounding box.
    """
    gray = img.convert("L")
    inverted = ImageOps.invert(gray)
    # Create a binary image: pixels below 50 become black; others white.
    bw = inverted.point(lambda x: 0 if x < 50 else 255, '1')
    bbox = bw.getbbox()
    if bbox:
        return img.crop(bbox)
    return img

def preprocess_image(image_bytes):
    """
    Pre-process the image:
      1. Open and convert to RGB.
      2. Dynamically crop using inverted grayscale.
      3. Center-crop to a square.
      4. Resize to 224x224 using high-quality LANCZOS resampling.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = dynamic_crop(img)
        width, height = img.size
        min_dim = min(width, height)
        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        img = img.crop((left, top, left + min_dim, top + min_dim))
        img = img.resize((224, 224), Image.LANCZOS)
        return img
    except Exception as e:
        raise Exception("Preprocessing error: " + str(e))

def parse_result(result):
    """
    Parse the result from the API if it is a string.
    Expected format: "Prediction: <class> (Confidence: <confidence>)"
    Returns a tuple: (prediction, confidence)
    """
    match = re.search(r"Prediction:\s*([A-Za-z0-9_]+)\s*\(Confidence:\s*([\d\.]+)\)", result)
    if match:
        prediction = match.group(1)
        confidence = float(match.group(2))
        return prediction, confidence
    else:
        # Fallback: return the full string as prediction with confidence 0
        return result, 0

@app.route('/')
def index():
    return "Predict API is running. Use POST /predict to analyze an image."

@app.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    # Retrieve additional form fields (if any)
    plant_type = request.form.get("plantType", "unknown")
    water_freq = request.form.get("waterFreq", "unknown")
    language = request.form.get("language", "english")
    
    # Retrieve the image from form data (key "image") or raw request data
    if 'image' in request.files:
        image_bytes = request.files['image'].read()
    elif request.data:
        image_bytes = request.data
    else:
        return jsonify({'error': 'No image provided'}), 400

    try:
        preprocessed_img = preprocess_image(image_bytes)
    except Exception as e:
        logging.error("Preprocessing failed: " + str(e))
        return jsonify({'error': f'Image preprocessing failed: {str(e)}'}), 500

    try:
        # Save the pre-processed image to a temporary file.
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            preprocessed_img.save(tmp, format="PNG")
            tmp.flush()
            tmp_path = tmp.name

        # Call the binary API first using the parameter name "image"
        binary_result = binary_client.predict(
            image=handle_file(tmp_path),
            api_name="/predict"
        )
        logging.info(f"Binary API result: {binary_result}")

        # Extract prediction from binary result:
        if isinstance(binary_result, str):
            binary_prediction, binary_confidence = parse_result(binary_result)
        else:
            binary_prediction = binary_result.get("prediction") or binary_result.get("Prediction")
            binary_confidence = binary_result.get("confidence", 0)

        # Determine status and recommendation
        if binary_prediction == "Healthy" and binary_confidence >= HEALTHY_THRESHOLD:
            status = "Healthy_plants"
            recommendation = f"Your {plant_type} appears healthy. Continue your regular care routine."
        else:
            # Otherwise, call the multi-class API for refined diagnosis.
            multi_result = multi_client.predict(
                image=handle_file(tmp_path),
                api_name="/predict"
            )
            logging.info(f"Multiclass API result: {multi_result}")
            if isinstance(multi_result, str):
                status, _ = parse_result(multi_result)
            else:
                status = multi_result.get("prediction") or multi_result.get("Prediction") or "Unknown"
            recommendation = (
                f"Your {plant_type} shows signs of {status}. "
                f"Consider adjusting your care routine. Water frequency: {water_freq} days. (Language: {language})"
            )

        # Return response matching frontend expectations.
        return jsonify({
            "status": status,
            "recommendation": recommendation
        })
    except Exception as e:
        logging.error("Prediction error: " + traceback.format_exc())
        return jsonify({'error': 'Prediction failed: ' + str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5002))
    app.run(host='0.0.0.0', port=port, debug=True)
