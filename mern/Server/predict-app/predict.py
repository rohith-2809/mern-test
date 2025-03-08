import os
import logging
import traceback
import io
import numpy as np
import requests
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
import tensorflow as tf  # <-- Import TensorFlow
from tensorflow.keras.models import load_model  # Use TensorFlow's built-in Keras
from PIL import Image, ImageEnhance, ImageOps

# Environment variables for model URLs
BINARY_MODEL_URL = os.environ.get(
    "BINARY_MODEL_URL",
    "https://huggingface.co/vittamraj/predict-binary/resolve/main/pp2v2.keras"
)
MULTI_MODEL_URL = os.environ.get(
    "MULTI_MODEL_URL",
    "https://huggingface.co/vittamraj/predict-Multiclass/resolve/main/pp5v6.keras"
)

# Other environment variables
NORMALIZATION_MODE = os.environ.get("NORMALIZATION_MODE", "minus1_to_1")
USE_TEMPERATURE_SCALING = os.environ.get("USE_TEMPERATURE_SCALING", "True").lower() == "true"
TEMPERATURE = float(os.environ.get("TEMPERATURE", 2.0))
NUM_AUGMENTATIONS = int(os.environ.get("NUM_AUGMENTATIONS", 5))

app = Flask(__name__)
CORS(app, supports_credentials=True)
logging.basicConfig(level=logging.INFO)

def load_model_from_url(url: str):
    """
    Downloads a Keras model file from the given URL and loads it into memory
    without saving it permanently to disk.
    """
    logging.info(f"Loading model from {url}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()

    # Save to a temporary file, then load with Keras
    with tempfile.NamedTemporaryFile(suffix=".keras") as tmp:
        for chunk in response.iter_content(chunk_size=8192):
            tmp.write(chunk)
        tmp.flush()
        model = load_model(tmp.name)
    logging.info(f"Model loaded from {url}")
    return model

# Attempt to load the binary classification model
try:
    binary_model = load_model_from_url(BINARY_MODEL_URL)
except Exception as e:
    logging.error(f"Binary model loading failed: {e}")
    binary_model = None

# Attempt to load the multi-disease classification model
try:
    multi_model = load_model_from_url(MULTI_MODEL_URL)
except Exception as e:
    logging.error(f"Multi-disease model loading failed: {e}")
    multi_model = None

# Class labels
binary_classes = ["Diseased", "Healthy"]
multi_disease_classes = [
    "Guava_Canker",
    "Guava_Dot",
    "Guava_Mummification",
    "Guava_Rust",
    "Healty_plants",
    "Money_plant_Bacterial_wilt_disease",
    "Money_plant_Manganese Toxicity",
    "Neem_Alternaria",
    "Neem_Dieback",
    "Neem_Leaf_Blight",
    "Neem_Leaf_Miners",
    "Neem_Leaf_Miners_Powdery_Mildew",
    "Neem_Powdery_Mildew",
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold"
]

def softmax(x):
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()

def apply_temperature_scaling(logits, temperature):
    return softmax(logits / temperature)

def dynamic_crop(img):
    gray = img.convert("L")
    inverted = ImageOps.invert(gray)
    bw = inverted.point(lambda x: 0 if x < 50 else 255, '1')
    bbox = bw.getbbox()
    if bbox:
        return img.crop(bbox)
    return img

def basic_augmentations(img):
    augmented_images = []
    # Original
    augmented_images.append(img)
    # Horizontal flip
    augmented_images.append(img.transpose(Image.FLIP_LEFT_RIGHT))
    # Rotate by 15 degrees
    augmented_images.append(img.rotate(15))
    # Rotate by -15 degrees
    augmented_images.append(img.rotate(-15))
    # Brightness enhancement
    bright_enhancer = ImageEnhance.Brightness(img)
    augmented_images.append(bright_enhancer.enhance(1.1))
    # Contrast enhancement
    contrast_enhancer = ImageEnhance.Contrast(img)
    augmented_images.append(contrast_enhancer.enhance(1.1))
    return augmented_images

def preprocess_and_augment_image(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = dynamic_crop(img)
        width, height = img.size
        min_dim = min(width, height)
        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        img = img.crop((left, top, left + min_dim, top + min_dim))
        img = img.resize((224, 224), Image.LANCZOS)
        contrast_enhancer = ImageEnhance.Contrast(img)
        img = contrast_enhancer.enhance(1.0)
        brightness_enhancer = ImageEnhance.Brightness(img)
        img = brightness_enhancer.enhance(1.0)
        aug_images = basic_augmentations(img)

        processed_images = []
        for aug_img in aug_images:
            img_array = np.array(aug_img, dtype=np.float32)
            if NORMALIZATION_MODE == "minus1_to_1":
                img_array = (img_array / 127.5) - 1.0
            else:
                img_array = img_array / 255.0
            img_array = np.expand_dims(img_array, axis=0)
            processed_images.append(img_array)

        return processed_images
    except Exception as e:
        logging.error(f"Error in preprocessing: {e}")
        raise

@app.route('/')
def index():
    return "Predict App is running. Use POST /predict to analyze an image."

@app.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    # Ensure both models are loaded
    if binary_model is None or multi_model is None:
        return jsonify({'error': 'One or more models are not loaded.'}), 500

    # Retrieve image from form data or raw request
    if 'image' in request.files:
        image_bytes = request.files['image'].read()
    elif request.data:
        image_bytes = request.data
    else:
        return jsonify({'error': 'No image provided'}), 400

    try:
        processed_images = preprocess_and_augment_image(image_bytes)
    except Exception as e:
        return jsonify({'error': f'Image processing failed: {str(e)}'}), 500

    try:
        binary_predictions = []
        multi_predictions = []

        for img in processed_images:
            # Use TensorFlow for array manipulation, if desired
            img_tensor = tf.convert_to_tensor(img, dtype=tf.float32)

            # Binary prediction
            binary_logits = np.array(binary_model.predict(img_tensor)[0])
            if USE_TEMPERATURE_SCALING:
                binary_probs = apply_temperature_scaling(binary_logits, TEMPERATURE)
            else:
                if not np.isclose(np.sum(binary_logits), 1.0, atol=1e-3):
                    binary_probs = softmax(binary_logits)
                else:
                    binary_probs = binary_logits
            binary_predictions.append(binary_probs)

            # Multi prediction
            multi_logits = np.array(multi_model.predict(img_tensor)[0])
            if not np.isclose(np.sum(multi_logits), 1.0, atol=1e-3):
                multi_probs = softmax(multi_logits)
            else:
                multi_probs = multi_logits
            multi_predictions.append(multi_probs)

        # Ensemble
        binary_avg = np.mean(binary_predictions, axis=0)
        multi_avg = np.mean(multi_predictions, axis=0)
        binary_std = np.std(binary_predictions, axis=0)
        multi_std = np.std(multi_predictions, axis=0)

        # Binary
        binary_pred_index = np.argmax(binary_avg)
        binary_confidence = float(binary_avg[binary_pred_index])
        binary_confidence_interval = (
            float(binary_avg[binary_pred_index] - binary_std[binary_pred_index]),
            float(binary_avg[binary_pred_index] + binary_std[binary_pred_index])
        )
        binary_prediction = ["Diseased", "Healthy"][binary_pred_index]

        logging.info(f"Binary ensemble avg: {binary_avg}, std: {binary_std}")
        logging.info(f"Binary prediction: {binary_prediction} conf: {binary_confidence:.4f}")

        HEALTHY_THRESHOLD = 0.5

        if binary_prediction == "Healthy" and binary_confidence >= HEALTHY_THRESHOLD:
            result = {
                'prediction': "Healty_plants",
                'confidence': binary_confidence,
                'confidence_interval': binary_confidence_interval,
                'model_used': "binary",
                'binary_output': binary_avg.tolist()
            }
        else:
            multi_pred_index = np.argmax(multi_avg)
            multi_confidence = float(multi_avg[multi_pred_index])
            multi_confidence_interval = (
                float(multi_avg[multi_pred_index] - multi_std[multi_pred_index]),
                float(multi_avg[multi_pred_index] + multi_std[multi_pred_index])
            )
            disease_prediction = [
                "Guava_Canker",
                "Guava_Dot",
                "Guava_Mummification",
                "Guava_Rust",
                "Healty_plants",
                "Money_plant_Bacterial_wilt_disease",
                "Money_plant_Manganese Toxicity",
                "Neem_Alternaria",
                "Neem_Dieback",
                "Neem_Leaf_Blight",
                "Neem_Leaf_Miners",
                "Neem_Leaf_Miners_Powdery_Mildew",
                "Neem_Powdery_Mildew",
                "Tomato___Bacterial_spot",
                "Tomato___Early_blight",
                "Tomato___Late_blight",
                "Tomato___Leaf_Mold"
            ][multi_pred_index]

            result = {
                'prediction': disease_prediction,
                'confidence': multi_confidence,
                'confidence_interval': multi_confidence_interval,
                'binary_prediction': binary_prediction,
                'binary_confidence': binary_confidence,
                'binary_output': binary_avg.tolist(),
                'multi_raw_output': multi_avg.tolist()
            }

        return jsonify(result)
    except Exception as e:
        logging.error("Prediction error: " + traceback.format_exc())
        return jsonify({'error': 'Prediction failed: ' + str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5002))
    app.run(host='0.0.0.0', port=port, debug=True)
