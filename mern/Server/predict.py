from flask import Flask, request, jsonify
import tensorflow as tf
import numpy as np
from PIL import Image, ImageEnhance, ImageOps
import io
from flask_cors import CORS
import logging
import traceback

app = Flask(__name__)
CORS(app, supports_credentials=True)
logging.basicConfig(level=logging.INFO)

# Configuration options
NORMALIZATION_MODE = "minus1_to_1"
USE_TEMPERATURE_SCALING = True
TEMPERATURE = 2.0  # Adjust this value based on calibration experiments
# We'll use several augmented images for test-time augmentation (TTA)
# The more augmentations, the more robust (but the slower)
NUM_AUGMENTATIONS = 5

# Load the binary classification model
BINARY_MODEL_PATH = r"E:\mern-test\mern\Server\pp2v2.keras"   # Update as needed
try:
    binary_model = tf.keras.models.load_model(BINARY_MODEL_PATH)
    logging.info(f"Binary model loaded successfully from {BINARY_MODEL_PATH}")
except Exception as e:
    logging.error(f"Binary model loading failed: {e}")
    binary_model = None

# Load the multi-disease classification model
MULTI_MODEL_PATH = r"E:\mern-test\mern\Server\pp5v6.keras"     # Update as needed
try:
    multi_model = tf.keras.models.load_model(MULTI_MODEL_PATH)
    logging.info(f"Multi-disease model loaded successfully from {MULTI_MODEL_PATH}")
except Exception as e:
    logging.error(f"Multi-disease model loading failed: {e}")
    multi_model = None

# Disease classification classes
# Note: Adjust the order to match the training of your binary model.
binary_classes = ["Diseased", "Healthy"]
multi_disease_classes = [
    "Guava_Canker",
    "Guava_Dot",
    "Guava_Mummification",
    "Guava_Rust",
    "Healty_plants",  # keeping original spelling for consistency
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
    # Divide logits by the temperature then compute softmax.
    return softmax(logits / temperature)

def dynamic_crop(img):
    """
    Attempt to crop the image dynamically by removing uniform background.
    This implementation converts the image to grayscale, inverts it,
    then uses a threshold to compute a bounding box.
    """
    gray = img.convert("L")
    inverted = ImageOps.invert(gray)
    # Binarize the image with a threshold value; adjust 50 as needed.
    bw = inverted.point(lambda x: 0 if x < 50 else 255, '1')
    bbox = bw.getbbox()
    if bbox:
        return img.crop(bbox)
    return img

def basic_augmentations(img):
    """
    Apply basic augmentations: horizontal flip, rotation, brightness,
    and contrast adjustments. Returns a list of augmented images.
    """
    augmented_images = []
    # Original
    augmented_images.append(img)
    # Horizontal flip
    augmented_images.append(img.transpose(Image.FLIP_LEFT_RIGHT))
    # Rotate by 15 degrees (clockwise)
    augmented_images.append(img.rotate(15))
    # Rotate by -15 degrees (counter-clockwise)
    augmented_images.append(img.rotate(-15))
    # Brightness enhancement
    bright_enhancer = ImageEnhance.Brightness(img)
    augmented_images.append(bright_enhancer.enhance(1.1))
    # Contrast enhancement
    contrast_enhancer = ImageEnhance.Contrast(img)
    augmented_images.append(contrast_enhancer.enhance(1.1))
    return augmented_images

def preprocess_and_augment_image(image_bytes):
    """
    Loads the image, applies dynamic cropping, center-crops and resizes,
    adjusts brightness/contrast, then generates multiple augmented versions
    for test-time augmentation.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        # Dynamic crop to remove background if possible
        img = dynamic_crop(img)

        # Center crop: ensure a square image based on the smallest dimension
        width, height = img.size
        min_dim = min(width, height)
        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        img = img.crop((left, top, left + min_dim, top + min_dim))

        # Resize image to 224x224 using LANCZOS filter
        img = img.resize((224, 224), Image.LANCZOS)

        # Optionally adjust brightness and contrast (tweak factors as needed)
        contrast_enhancer = ImageEnhance.Contrast(img)
        img = contrast_enhancer.enhance(1.0)
        brightness_enhancer = ImageEnhance.Brightness(img)
        img = brightness_enhancer.enhance(1.0)

        # Generate a set of augmented images for TTA
        aug_images = basic_augmentations(img)

        processed_images = []
        for aug_img in aug_images:
            img_array = np.array(aug_img, dtype=np.float32)
            if NORMALIZATION_MODE == "minus1_to_1":
                img_array = (img_array / 127.5) - 1.0
            else:
                img_array = img_array / 255.0
            # Add batch dimension
            img_array = np.expand_dims(img_array, axis=0)
            processed_images.append(img_array)

        return processed_images
    except Exception as e:
        logging.error(f"Error in preprocessing and augmentation: {e}")
        raise

@app.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    # Check if models are loaded
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
        # For ensemble predictions, run the image through each augmentation.
        binary_predictions = []
        multi_predictions = []

        for img in processed_images:
            # Predict with binary model
            binary_logits = np.array(binary_model.predict(img)[0])
            if USE_TEMPERATURE_SCALING:
                binary_probs = apply_temperature_scaling(binary_logits, TEMPERATURE)
            else:
                if not np.isclose(np.sum(binary_logits), 1.0, atol=1e-3):
                    binary_probs = softmax(binary_logits)
                else:
                    binary_probs = binary_logits
            binary_predictions.append(binary_probs)

            # Predict with multi-disease model
            multi_logits = np.array(multi_model.predict(img)[0])
            if not np.isclose(np.sum(multi_logits), 1.0, atol=1e-3):
                multi_probs = softmax(multi_logits)
            else:
                multi_probs = multi_logits
            multi_predictions.append(multi_probs)

        # Average predictions across augmentations (ensemble)
        binary_avg = np.mean(binary_predictions, axis=0)
        multi_avg = np.mean(multi_predictions, axis=0)
        binary_std = np.std(binary_predictions, axis=0)
        multi_std = np.std(multi_predictions, axis=0)

        # Determine binary prediction and a rough confidence interval
        binary_pred_index = np.argmax(binary_avg)
        binary_confidence = float(binary_avg[binary_pred_index])
        binary_confidence_interval = (
            float(binary_avg[binary_pred_index] - binary_std[binary_pred_index]),
            float(binary_avg[binary_pred_index] + binary_std[binary_pred_index])
        )
        binary_prediction = binary_classes[binary_pred_index]

        logging.info(f"Binary model ensemble avg: {binary_avg}, std: {binary_std}")
        logging.info(f"Binary prediction: {binary_prediction} with confidence: {binary_confidence:.4f}")

        HEALTHY_THRESHOLD = 0.5  # Adjust threshold as needed

        # If the binary classifier is confidently predicting Healthy, return that result.
        if binary_prediction == "Healthy" and binary_confidence >= HEALTHY_THRESHOLD:
            result = {
                'prediction': "Healty_plants",
                'confidence': binary_confidence,
                'confidence_interval': binary_confidence_interval,
                'model_used': "binary",
                'binary_output': binary_avg.tolist()
            }
        else:
            # Use the multi-disease classifier for detailed diagnosis.
            multi_pred_index = np.argmax(multi_avg)
            multi_confidence = float(multi_avg[multi_pred_index])
            multi_confidence_interval = (
                float(multi_avg[multi_pred_index] - multi_std[multi_pred_index]),
                float(multi_avg[multi_pred_index] + multi_std[multi_pred_index])
            )
            disease_prediction = multi_disease_classes[multi_pred_index]
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
    # Run on port 5002 (adjust if needed)
    app.run(host='0.0.0.0', port=5002, debug=True)
