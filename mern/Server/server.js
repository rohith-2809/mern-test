const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");
const multer = require("multer");
const axios = require("axios");
const jwt = require("jsonwebtoken");
const bcrypt = require("bcrypt");
require("dotenv").config();

const app = express();

// Configure CORS to allow your client domain
const corsOptions = {
  origin: "https://mern-test-client.onrender.com", // Adjust as needed
  methods: "GET,HEAD,PUT,PATCH,POST,DELETE",
  credentials: true,
  optionsSuccessStatus: 200,
};
app.use(cors(corsOptions));

app.use(express.json());

// Replace the local URI with your Atlas connection string
const MONGODB_URI =
  process.env.MONGODB_URI ||
  "mongodb+srv://myAppUser:890iopjklnm@plantdiseasedetection.uhd0o.mongodb.net/?retryWrites=true&w=majority&appName=Plantdiseasedetection";

// Set external endpoints from environment variables
const FLASK_URL = process.env.FLASK_URL || "https://predict-app-mawg.onrender.com";
const GEMINI_URL = process.env.GEMINI_URL || "https://agent-app.onrender.com";
const JWT_SECRET = process.env.JWT_SECRET || "secretkey";

// Connect to MongoDB
mongoose
  .connect(MONGODB_URI)
  .then(() => console.log("✅ MongoDB connected"))
  .catch((err) => {
    console.error("❌ MongoDB connection error:", err);
  });

// User Schema
const UserSchema = new mongoose.Schema({
  username: { type: String, required: true },
  email: { type: String, unique: true, required: true },
  password: { type: String, required: true },
  history: [
    {
      plantType: String,
      status: String,
      recommendation: String,
      analyzedAt: { type: Date, default: Date.now },
    },
  ],
});

const User = mongoose.model("users", UserSchema);

// ---------------------------------------------------------
// ROOT/HEALTH CHECK ROUTE
app.get("/", (req, res) => {
  res.send("Node server is running. Use /register, /login, /analyze, etc.");
});
// ---------------------------------------------------------

// Registration endpoint
app.post("/register", async (req, res) => {
  try {
    const { username, email, password } = req.body;
    if (await User.findOne({ email })) {
      return res.status(400).json({ message: "User already exists" });
    }
    const hashedPassword = await bcrypt.hash(password, 10);
    const user = new User({
      username,
      email,
      password: hashedPassword,
      history: [],
    });
    await user.save();
    res.json({ message: "✅ User registered successfully!" });
  } catch (error) {
    console.error("Registration error details:", error);
    console.error("Stack trace:", error.stack);
    res.status(500).json({ error: error.message });
  }
});

// Login endpoint
app.post("/login", async (req, res) => {
  try {
    const { email, password } = req.body;
    console.log("Login attempt for:", email);
    const user = await User.findOne({ email });
    if (!user || !(await bcrypt.compare(password, user.password))) {
      console.log("Invalid credentials");
      return res.status(401).json({ message: "❌ Invalid credentials" });
    }
    const token = jwt.sign({ userId: user._id }, JWT_SECRET, { expiresIn: "1h" });
    res.json({ token });
  } catch (error) {
    console.error("Login error details:", error);
    console.error("Stack trace:", error.stack);
    res.status(500).json({ error: error.message });
  }
});

// Middleware to protect routes
const authenticateUser = (req, res, next) => {
  const token = req.headers.authorization;
  if (!token) return res.status(401).json({ message: "Access denied" });

  jwt.verify(token, JWT_SECRET, (err, decoded) => {
    if (err) {
      console.error("JWT verification error:", err);
      return res.status(401).json({ message: "Invalid or expired token" });
    }
    req.userId = decoded.userId;
    next();
  });
};

// Set up Multer for image uploads (using memory storage)
const storage = multer.memoryStorage();
const upload = multer({ storage });

// Analyze Endpoint

// Analyze Endpoint
app.post("/analyze", upload.single("image"), async (req, res) => {
  console.log("Received /analyze request");
  try {
    // Retrieve form fields
    const { plantType, waterFreq } = req.body;
    const image = req.file;
    if (!image) {
      console.error("No image provided in the request");
      return res.status(400).json({ message: "Image is required" });
    }
    console.log("Plant Type:", plantType, "Water Frequency:", waterFreq);

    // Call the predict Flask API
    const flaskEndpoint = `${FLASK_URL}/predict`;
    console.log("Calling predict API at:", flaskEndpoint);
    const flaskResponse = await axios.post(
      flaskEndpoint,
      image.buffer,
      { headers: { "Content-Type": "application/octet-stream" } }
    );
    console.log("Predict API response:", flaskResponse.data);

    // Determine prediction:
    let status;
    if (typeof flaskResponse.data === "string") {
      // If response is a string, try to extract prediction via regex
      const regex = /Prediction:\s*([A-Za-z0-9_]+)\s*\(Confidence:\s*([\d.]+)\)/i;
      const match = regex.exec(flaskResponse.data);
      if (match) {
        status = match[1];
        console.log("Parsed prediction from string:", status);
      } else {
        throw new Error("No prediction returned from predict API");
      }
    } else {
      // Try both lower-case and capitalized keys
      status = flaskResponse.data.prediction || flaskResponse.data.Prediction;
      if (!status) {
        throw new Error("No prediction returned from predict API");
      }
    }
    console.log("Status (prediction):", status);

    // Call the recommendation (agent) API with proper JSON header.
    const geminiEndpoint = `${GEMINI_URL}/recommend`;
    console.log("Calling recommendation API at:", geminiEndpoint);
    let recommendation;
    try {
      const geminiResponse = await axios.post(
        geminiEndpoint,
        {
          status,
          plantType,
          waterFreq: parseInt(waterFreq, 10),
        },
        {
          headers: { "Content-Type": "application/json" },
        }
      );
      console.log("Recommendation API response:", geminiResponse.data);
      recommendation = geminiResponse.data.recommendation;
    } catch (agentError) {
      console.error("Error fetching recommendation:", agentError.message);
      recommendation = "Sorry, cure recommendations are not available right now.";
    }

    // Return the combined response to the frontend.
    res.json({
      prediction: status,
      recommendation,
    });
  } catch (error) {
    console.error("Analyze error details:", error.message);
    console.error("Stack trace:", error.stack);
    res.status(500).json({ error: error.message });
  }
});


// Analyze Endpoint
// Get user history (Protected endpoint)
app.get("/history", authenticateUser, async (req, res) => {
  try {
    const user = await User.findById(req.userId);
    if (!user) return res.status(404).json({ message: "User not found" });
    res.json({ username: user.username, history: user.history });
  } catch (error) {
    console.error("History error details:", error);
    console.error("Stack trace:", error.stack);
    res.status(500).json({ error: error.message });
  }
});

// Start the server on 0.0.0.0 with the specified port
const PORT = process.env.PORT || 5000;
app.listen(PORT, "0.0.0.0", () => {
  console.log(`🚀 Server running at http://0.0.0.0:${PORT}`);
});
