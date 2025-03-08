import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"  # Disable GPU

import logging
import traceback
import io
import tempfile
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageOps  # For image processing

# Import gradio_client to call the remote Gradio APIs
from gradio_client import Client, handle_file

app = Flask(__name__)
CORS(app, supports_credentials=True)
logging.basicConfig(level=logging.INFO)

# Instantiate Gradio API clients
binary_client = Client("vittamraj/predict-binary-api")
multi_client = Client("vittamraj/predict-MultiClass-api")

# Define a healthy threshold (adjust as needed)
HEALTHY_THRESHOLD = 0.5

def dynamic_crop(img):
    """
    Dynamically crop the image by inverting the grayscale image,
    thresholding it, and using the bounding box to crop.
    """
    gray = img.convert("L")
    inverted = ImageOps.invert(gray)
    # Convert to binary image: pixels below 50 become black, others white.
    bw = inverted.point(lambda x: 0 if x < 50 else 255, '1')
    bbox = bw.getbbox()
    if bbox:
        return img.crop(bbox)
    return img

def preprocess_image(image_bytes):
    """
    Pre-process the image:
      1. Open and convert to RGB.
      2. Dynamically crop using the inverted grayscale.
      3. Center-crop to a square.
      4. Resize to 224x224 using high-quality resampling.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        # Apply dynamic crop
        img = dynamic_crop(img)
        # Center crop to square
        width, height = img.size
        min_dim = min(width, height)
        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        img = img.crop((left, top, left + min_dim, top + min_dim))
        # Resize to 224x224
        img = img.resize((224, 224), Image.LANCZOS)
        return img
    except Exception as e:
        raise Exception("Preprocessing error: " + str(e))

@app.route('/')
def index():
    return "Predict App is running. Use POST /predict to analyze an image."

@app.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    # Retrieve image from form data or raw request body
    if 'image' in request.files:
        image_bytes = request.files['image'].read()
    elif request.data:
        image_bytes = request.data
    else:
        return jsonify({'error': 'No image provided'}), 400

    try:
        # Pre-process the image
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

        # Call the binary API first.
        # If your binary API expects an image file, you may use "image" instead of "input_data".
        binary_result = binary_client.predict(
            input_data=handle_file(tmp_path),
            api_name="/predict"
        )
        logging.info(f"Binary API result: {binary_result}")

        binary_prediction = binary_result.get("prediction")
        binary_confidence = binary_result.get("confidence", 0)

        # If the plant is predicted as Healthy with high confidence, return that result.
        if binary_prediction == "Healthy" and binary_confidence >= HEALTHY_THRESHOLD:
            combined_result = {
                'prediction': "Healty_plants",
                'confidence': binary_confidence,
                'model_used': "binary",
                'binary_output': binary_result
            }
        else:
            # Otherwise, use the multi-class API to refine the diagnosis.
            multi_result = multi_client.predict(
                image=handle_file(tmp_path),
                api_name="/predict"
            )
            logging.info(f"Multiclass API result: {multi_result}")

            combined_result = {
                'prediction': multi_result.get("prediction"),
                'confidence': multi_result.get("confidence"),
                'binary_prediction': binary_prediction,
                'binary_confidence': binary_confidence,
                'binary_output': binary_result,
                'multi_output': multi_result
            }

        return jsonify(combined_result)
    except Exception as e:
        logging.error("Prediction error: " + traceback.format_exc())
        return jsonify({'error': 'Prediction failed: ' + str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5002))
    app.run(host='0.0.0.0', port=port, debug=True)
