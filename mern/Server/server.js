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
  origin: "https://mern-test-client.onrender.com", // adjust as needed
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
const FLASK_URL =
  process.env.FLASK_URL || "https://predict-app-mawg.onrender.com";
const GEMINI_URL =
  process.env.GEMINI_URL || "https://agent-app.onrender.com";
const JWT_SECRET = process.env.JWT_SECRET || "secretkey";
// Use a separate secret for refresh tokens if provided; otherwise, use the same one.
const REFRESH_JWT_SECRET = process.env.REFRESH_JWT_SECRET || JWT_SECRET;

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
  // Optionally, you could store refresh tokens here for extra security.
});

const User = mongoose.model("users", UserSchema);

// ---------------------------------------------------------
// ROOT/HEALTH CHECK ROUTE
app.get("/", (req, res) => {
  res.send("Node server is running. Use /register, /login, /refresh, /analyze, etc.");
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
    // Generate a short-lived access token and a long-lived refresh token
    const accessToken = jwt.sign({ userId: user._id }, JWT_SECRET, { expiresIn: "15m" });
    const refreshToken = jwt.sign({ userId: user._id }, REFRESH_JWT_SECRET, { expiresIn: "7d" });
    res.json({ accessToken, refreshToken });
  } catch (error) {
    console.error("Login error details:", error);
    console.error("Stack trace:", error.stack);
    res.status(500).json({ error: error.message });
  }
});

// Refresh endpoint
app.post("/refresh", async (req, res) => {
  try {
    const { refreshToken } = req.body;
    if (!refreshToken) return res.status(400).json({ message: "Refresh token is required" });
    
    jwt.verify(refreshToken, REFRESH_JWT_SECRET, (err, decoded) => {
      if (err) {
        console.error("Refresh token verification error:", err);
        return res.status(401).json({ message: "Invalid or expired refresh token" });
      }
      const newAccessToken = jwt.sign({ userId: decoded.userId }, JWT_SECRET, { expiresIn: "15m" });
      console.log("New access token generated for user:", decoded.userId);
      return res.json({ accessToken: newAccessToken });
    });
  } catch (error) {
    console.error("Refresh token error details:", error);
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
// This endpoint receives an image and additional form fields,
// calls the external Flask predict API and the agent recommendation API,
// and returns a combined response.
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

    // Use the 'prediction' field from the predict API response as the status
    const status = flaskResponse.data.prediction;
    if (!status) {
      throw new Error("No prediction returned from predict API");
    }
    console.log("Status (prediction):", status);

    // Call the recommendation (agent) API
    const geminiEndpoint = `${GEMINI_URL}/recommend`;
    console.log("Calling recommendation API at:", geminiEndpoint);
    const geminiResponse = await axios.post(geminiEndpoint, {
      status,
      plantType,
      waterFreq: parseInt(waterFreq, 10),
    });
    console.log("Recommendation API response:", geminiResponse.data);

    // Return the combined response to the frontend
    res.json({
      status,
      recommendation: geminiResponse.data.recommendation,
    });
  } catch (error) {
    console.error("Analyze error details:", error.message);
    console.error("Stack trace:", error.stack);
    res.status(500).json({ error: error.message });
  }
});

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
