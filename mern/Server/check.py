from flask import Flask, request, jsonify
from tensorflow.keras.models import load_model
import numpy as np
from PIL import Image
import os

# Load the pre-trained model
MODEL_PATH = r"E:\mern-test\mern\Server\pp5v6.keras"
model = load_model(MODEL_PATH)

# Define your class labels in the same order as your model output
class_labels = [
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

# Create Flask app instance
app = Flask(__name__)

# A helper function to preprocess images for prediction.
def preprocess_image(image, target_size=(224, 224)):
    if image.mode != "RGB":
        image = image.convert("RGB")
    image = image.resize(target_size)
    image = np.array(image) / 255.0  # normalize pixel values
    image = np.expand_dims(image, axis=0)
    return image

# Route for uploading an image and getting a prediction.
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Ensure an image file is provided.
        if "file" not in request.files:
            return jsonify({"error": "No file part in the request"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        try:
            image = Image.open(file.stream)
            processed_image = preprocess_image(image)
            prediction = model.predict(processed_image)
            predicted_idx = np.argmax(prediction, axis=1)[0]
            predicted_label = class_labels[predicted_idx]
            return jsonify({"prediction": predicted_label})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Basic HTML form for image upload
    return '''
    <!doctype html>
    <html>
      <head>
        <title>Plant Disease Prediction</title>
      </head>
      <body>
        <h1>Upload an Image for Disease Prediction</h1>
        <form method="POST" enctype="multipart/form-data">
          <input type="file" name="file" accept="image/*">
          <input type="submit" value="Predict">
        </form>
      </body>
    </html>
    '''

# Route to run predictions on a set of predefined test image paths.
@app.route("/test", methods=["GET"])
def test_predictions():
    # List of test image paths (update these paths if needed)
    test_image_paths = [
        r"D:\node_modules\new model\training_set\unhealthy_plants\neem\Alternaria\Alternaria27.jpg",
        r"D:\node_modules\new model\training_set\unhealthy_plants\neem\Dieback\Dieback2.jpg",
        r"D:\node_modules\new model\training_set\unhealthy_plants\neem\Leaf_Blight\8.png",
        r"D:\node_modules\new model\training_set\unhealthy_plants\neem\Leaf_Miners\Leaf_Miners8.jpg",
        r"D:\node_modules\new model\training_set\unhealthy_plants\neem\Leaf_Miners_Powdery_Mildew\Leaf_Miners_Powdery_Mildew8.jpg",
        r"D:\node_modules\new model\training_set\unhealthy_plants\neem\Powdery_Mildew\Powdery_Mildew8.jpg",
        r"D:\node_modules\new model\training_set\unhealthy_plants\guva\Canker\test_0_1015.jpeg",
        r"D:\node_modules\new model\training_set\unhealthy_plants\guva\Dot\0015_0008.JPG",
        r"D:\node_modules\new model\training_set\unhealthy_plants\guva\Mummification\test_0_2144.jpeg",
        r"D:\node_modules\new model\training_set\unhealthy_plants\guva\Rust\test_0_796.jpeg",
    ]
    results = {}

    for path in test_image_paths:
        if not os.path.exists(path):
            results[path] = "File not found"
            continue
        try:
            image = Image.open(path)
            processed_image = preprocess_image(image)
            prediction = model.predict(processed_image)
            predicted_idx = np.argmax(prediction, axis=1)[0]
            predicted_label = class_labels[predicted_idx]
            results[path] = predicted_label
        except Exception as e:
            results[path] = f"Error: {str(e)}"

    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, request, jsonify
from tensorflow.keras.models import load_model
import numpy as np
from PIL import Image
import os

# Load the pre-trained model
MODEL_PATH = r"E:\mern-test\mern\Server\pp5v6.keras"
model = load_model(MODEL_PATH)

# Define your class labels in the same order as your model output
class_labels = [
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

# Create Flask app instance
app = Flask(__name__)

# A helper function to preprocess images for prediction.
def preprocess_image(image, target_size=(224, 224)):
    if image.mode != "RGB":
        image = image.convert("RGB")
    image = image.resize(target_size)
    image = np.array(image) / 255.0  # normalize pixel values
    image = np.expand_dims(image, axis=0)
    return image

# Route for uploading an image and getting a prediction.
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Ensure an image file is provided.
        if "file" not in request.files:
            return jsonify({"error": "No file part in the request"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        try:
            image = Image.open(file.stream)
            processed_image = preprocess_image(image)
            prediction = model.predict(processed_image)
            predicted_idx = np.argmax(prediction, axis=1)[0]
            predicted_label = class_labels[predicted_idx]
            return jsonify({"prediction": predicted_label})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Basic HTML form for image upload
    return '''
    <!doctype html>
    <html>
      <head>
        <title>Plant Disease Prediction</title>
      </head>
      <body>
        <h1>Upload an Image for Disease Prediction</h1>
        <form method="POST" enctype="multipart/form-data">
          <input type="file" name="file" accept="image/*">
          <input type="submit" value="Predict">
        </form>
      </body>
    </html>
    '''

# Route to run predictions on a set of predefined test image paths.
@app.route("/test", methods=["GET"])
def test_predictions():
    # List of test image paths (update these paths if needed)
    test_image_paths = [
        r"D:\node_modules\new model\training_set\unhealthy_plants\neem\Alternaria\Alternaria27.jpg",
        r"D:\node_modules\new model\training_set\unhealthy_plants\neem\Dieback\Dieback2.jpg",
        r"D:\node_modules\new model\training_set\unhealthy_plants\neem\Leaf_Blight\8.png",
        r"D:\node_modules\new model\training_set\unhealthy_plants\neem\Leaf_Miners\Leaf_Miners8.jpg",
        r"D:\node_modules\new model\training_set\unhealthy_plants\neem\Leaf_Miners_Powdery_Mildew\Leaf_Miners_Powdery_Mildew8.jpg",
        r"D:\node_modules\new model\training_set\unhealthy_plants\neem\Powdery_Mildew\Powdery_Mildew8.jpg",
        r"D:\node_modules\new model\training_set\unhealthy_plants\guva\Canker\test_0_1015.jpeg",
        r"D:\node_modules\new model\training_set\unhealthy_plants\guva\Dot\0015_0008.JPG",
        r"D:\node_modules\new model\training_set\unhealthy_plants\guva\Mummification\test_0_2144.jpeg",
        r"D:\node_modules\new model\training_set\unhealthy_plants\guva\Rust\test_0_796.jpeg",
    ]
    results = {}

    for path in test_image_paths:
        if not os.path.exists(path):
            results[path] = "File not found"
            continue
        try:
            image = Image.open(path)
            processed_image = preprocess_image(image)
            prediction = model.predict(processed_image)
            predicted_idx = np.argmax(prediction, axis=1)[0]
            predicted_label = class_labels[predicted_idx]
            results[path] = predicted_label
        except Exception as e:
            results[path] = f"Error: {str(e)}"

    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
