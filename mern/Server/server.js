const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");
const multer = require("multer");
const axios = require("axios");
const jwt = require("jsonwebtoken");
const bcrypt = require("bcrypt");
const helmet = require("helmet");
const compression = require("compression");
const morgan = require("morgan");
const rateLimit = require("express-rate-limit");
require("dotenv").config();

const app = express();

// Use Helmet for security headers
app.use(helmet());

// Use compression for response compression
app.use(compression());

// Use morgan for HTTP request logging
app.use(morgan("dev"));

// Configure CORS to allow your client domain
const corsOptions = {
  origin: "https://mern-test-client.onrender.com", // Adjust as needed
  methods: "GET,HEAD,PUT,PATCH,POST,DELETE",
  credentials: true,
  optionsSuccessStatus: 200,
};
app.use(cors(corsOptions));

// Parse JSON and URL-encoded data
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Rate Limiter: Limit each IP to 100 requests per 15 minutes
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
});
app.use(limiter);

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

// Async handler to reduce try/catch redundancy in async routes
const asyncHandler = (fn) => (req, res, next) =>
  Promise.resolve(fn(req, res, next)).catch(next);

// ---------------------------------------------------------
// ROOT/HEALTH CHECK ROUTE
app.get("/", (req, res) => {
  res.send("Node server is running. Use /register, /login, /analyze, etc.");
});

// ---------------------------------------------------------
// Registration endpoint
app.post(
  "/register",
  asyncHandler(async (req, res) => {
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
  })
);

// Login endpoint
app.post(
  "/login",
  asyncHandler(async (req, res) => {
    const { email, password } = req.body;
    console.log("Login attempt for:", email);
    const user = await User.findOne({ email });
    if (!user || !(await bcrypt.compare(password, user.password))) {
      console.log("Invalid credentials");
      return res.status(401).json({ message: "❌ Invalid credentials" });
    }
    const token = jwt.sign({ userId: user._id }, JWT_SECRET, { expiresIn: "1h" });
    res.json({ token });
  })
);

// Middleware to protect routes with improved token extraction
const authenticateUser = (req, res, next) => {
  let token = req.headers.authorization;
  if (!token) return res.status(401).json({ message: "Access denied" });
  
  // Support Bearer token format
  if (token.startsWith("Bearer ")) {
    token = token.slice(7, token.length).trim();
  }
  
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

// Analyze Endpoint with user authentication and history update
app.post(
  "/analyze",
  authenticateUser,
  upload.single("image"),
  asyncHandler(async (req, res) => {
    console.log("Received /analyze request");
    const { plantType, waterFreq, language } = req.body;
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
    console.log("Predict API raw response:", flaskResponse.data);

    // Extract prediction from the response.
    let status;
    if (typeof flaskResponse.data === "string") {
      const regex = /Prediction:\s*([A-Za-z0-9_]+)\s*\(Confidence:\s*([\d.]+)\)/i;
      const match = regex.exec(flaskResponse.data);
      if (match) {
        status = match[1];
        console.log("Parsed prediction from string:", status);
      } else {
        console.warn("No prediction parsed from string; using fallback 'Unknown'");
        status = "Unknown";
      }
    } else {
      status =
        flaskResponse.data.prediction ||
        flaskResponse.data.Prediction ||
        flaskResponse.data.status;
      if (!status) {
        console.warn("No prediction found in JSON; using fallback 'Unknown'");
        status = "Unknown";
      }
    }
    console.log("Status (prediction):", status);

    // Call the recommendation (agent) API.
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
          language,
        },
        { headers: { "Content-Type": "application/json" } }
      );
      console.log("Recommendation API response:", geminiResponse.data);
      recommendation = geminiResponse.data.recommendation;
    } catch (agentError) {
      console.error("Error fetching recommendation:", agentError.message);
      recommendation = "Sorry, cure recommendations are not available right now.";
    }

    // Update user history in the database asynchronously (non-blocking)
    User.findByIdAndUpdate(req.userId, {
      $push: {
        history: {
          plantType,
          status,
          recommendation,
          analyzedAt: new Date(),
        },
      },
    }).then(() => {
      console.log("User history updated successfully");
    }).catch((updateError) => {
      console.error("Error updating user history:", updateError);
    });

    // Return the combined response to the frontend.
    res.json({
      prediction: status,
      recommendation,
    });
  })
);

// Get user history (Protected endpoint)
app.get(
  "/history",
  authenticateUser,
  asyncHandler(async (req, res) => {
    const user = await User.findById(req.userId);
    if (!user) return res.status(404).json({ message: "User not found" });
    res.json({ username: user.username, history: user.history });
  })
);

// Global Error Handling Middleware
app.use((err, req, res, next) => {
  console.error("Unhandled error:", err.stack);
  res.status(err.status || 500).json({ message: err.message || "Internal Server Error" });
});

// Start the server on 0.0.0.0 with the specified port
const PORT = process.env.PORT || 5000;
app.listen(PORT, "0.0.0.0", () => {
  console.log(`🚀 Server running at http://0.0.0.0:${PORT}`);
});
