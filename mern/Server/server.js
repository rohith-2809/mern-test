const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");
const multer = require("multer");
const axios = require("axios");
const jwt = require("jsonwebtoken");
const bcrypt = require("bcrypt");
require("dotenv").config();

const app = express();
app.use(cors());
app.use(express.json());

// Load environment variables with fallbacks
const MONGODB_URI = process.env.MONGODB_URI || "mongodb://127.0.0.1:27017/plant_disease_db";
const FLASK_URL = process.env.FLASK_URL || "http://127.0.0.1:5001";
const GEMINI_URL = process.env.GEMINI_URL || "http://127.0.0.1:5002";
const JWT_SECRET = process.env.JWT_SECRET || "secretkey";

// Connect to MongoDB (no deprecated options)
mongoose
  .connect(MONGODB_URI)
  .then(() => console.log("✅ MongoDB connected"))
  .catch((err) => console.error("❌ MongoDB connection error:", err));

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
    console.error("Registration error:", error);
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
    const token = jwt.sign(
      { userId: user._id },
      JWT_SECRET,
      { expiresIn: "1h" }
    );
    res.json({ token });
  } catch (error) {
    console.error("Login error:", error);
    res.status(500).json({ error: error.message });
  }
});

// Middleware to protect routes
const authenticateUser = (req, res, next) => {
  const token = req.headers.authorization;
  if (!token) return res.status(401).json({ message: "Access denied" });

  jwt.verify(token, JWT_SECRET, (err, decoded) => {
    if (err) return res.status(401).json({ message: "Invalid token" });
    req.userId = decoded.userId;
    next();
  });
};

// Set up Multer for image uploads
const storage = multer.memoryStorage();
const upload = multer({ storage });

// Analyze Endpoint (Authentication Removed)
app.post("/analyze", upload.single("image"), async (req, res) => {
  try {
    const { plantType, waterFreq } = req.body;
    const image = req.file;
    if (!image) {
      return res.status(400).json({ message: "Image is required" });
    }

    // Call Flask API for prediction
    const flaskResponse = await axios.post(
      `${FLASK_URL}/predict`,
      image.buffer,
      { headers: { "Content-Type": "application/octet-stream" } }
    );
    const status = flaskResponse.data.prediction;

    // Call Gemini API to get recommendation
    const geminiResponse = await axios.post(`${GEMINI_URL}/gemini`, {
      status,
      plantType,
      waterFreq: parseInt(waterFreq, 10),
    });

    res.json({
      status,
      recommendation: geminiResponse.data.recommendation,
    });
  } catch (error) {
    console.error("Analyze error:", error.message);
    res.status(500).json({ error: error.message });
  }
});

// Get user history (Protected)
app.get("/history", authenticateUser, async (req, res) => {
  try {
    const user = await User.findById(req.userId);
    if (!user) return res.status(404).json({ message: "User not found" });
    res.json({ username: user.username, history: user.history });
  } catch (error) {
    console.error("History error:", error.message);
    res.status(500).json({ error: error.message });
  }
});

// Start the server on 0.0.0.0
const PORT = process.env.PORT || 5000;
const HOST = "0.0.0.0";
app.listen(PORT, HOST, () => {
  console.log(`🚀 Server running at http://${HOST}:${PORT}`);
});
