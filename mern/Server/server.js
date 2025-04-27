// server.js
const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");
const helmet = require("helmet");
const morgan = require("morgan");
const multer = require("multer");
const sharp = require("sharp");
const axios = require("axios");
const jwt = require("jsonwebtoken");
const bcrypt = require("bcrypt");
const path = require("path");
const fs = require("fs");

// Configuration constants
const CLIENT_URL = "https://mern-test-client.onrender.com";
const MONGODB_URI = "mongodb+srv://myAppUser:890iopjklnm@plantdiseasedetection.uhd0o.mongodb.net/?retryWrites=true&w=majority&appName=Plantdiseasedetection";
const FLASK_URL = "https://predict-app-mawg.onrender.com";
const GEMINI_URL = "https://agent-app.onrender.com";
const JWT_SECRET = "your_jwt_secret_here";
const JWT_EXPIRES_IN = "1h";
const PORT = 5000;
const UPLOAD_DIR = path.join(__dirname, "uploads");

// Ensure upload directory exists
if (!fs.existsSync(UPLOAD_DIR)) fs.mkdirSync(UPLOAD_DIR);

// Connect to MongoDB
mongoose
  .connect(MONGODB_URI, { useNewUrlParser: true, useUnifiedTopology: true })
  .then(() => console.log("✅ MongoDB connected"))
  .catch((err) => {
    console.error("❌ MongoDB connection error:", err);
    process.exit(1);
  });

const app = express();

// Middleware
app.use(helmet());
app.use(morgan("combined"));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(
  cors({
    origin: CLIENT_URL,
    methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    credentials: true,
  })
);
// Serve uploaded images statically
app.use('/uploads', express.static(UPLOAD_DIR));

// Multer: store original and limit size
const storage = multer.diskStorage({
  destination: UPLOAD_DIR,
  filename: (req, file, cb) => {
    const unique = `${Date.now()}-${Math.round(Math.random() * 1e9)}`;
    const ext = path.extname(file.originalname);
    cb(null, `${unique}${ext}`);
  },
});
const upload = multer({
  storage,
  limits: { fileSize: 10 * 1024 * 1024 }, // 10MB max
  fileFilter: (req, file, cb) => {
    if (!file.mimetype.startsWith('image/')) return cb(new Error('Only image files allowed'), false);
    cb(null, true);
  }
});

// JWT auth middleware
const authenticateUser = (req, res, next) => {
  const auth = req.headers.authorization || "";
  const token = auth.startsWith('Bearer ') ? auth.split(' ')[1] : null;
  if (!token) return res.status(401).json({ message: 'Access denied: no token' });
  jwt.verify(token, JWT_SECRET, (err, decoded) => {
    if (err) {
      if (err.name === 'TokenExpiredError') return res.status(401).json({ message: 'Token expired' });
      return res.status(401).json({ message: 'Invalid token' });
    }
    req.userId = decoded.userId;
    next();
  });
};

// User model
const userSchema = new mongoose.Schema({
  username: { type: String, required: true },
  email: { type: String, unique: true, required: true },
  password: { type: String, required: true },
  history: [{
    plantType: String,
    status: String,
    recommendation: String,
    imageUrl: String,
    thumbnailUrl: String,
    analyzedAt: { type: Date, default: Date.now }
  }]
}, { timestamps: true });
const User = mongoose.model('User', userSchema);

// Routes
app.get('/', (req, res) => res.json({ message: 'Server is running' }));

// Register
app.post('/register', async (req, res, next) => {
  try {
    const { username, email, password } = req.body;
    if (!username || !email || !password) return res.status(400).json({ message: 'Missing fields' });
    if (await User.exists({ email })) return res.status(409).json({ message: 'User exists' });
    const hash = await bcrypt.hash(password,12);
    await new User({ username, email, password: hash }).save();
    res.status(201).json({ message: 'Registered' });
  } catch (e) { next(e); }
});

// Login
app.post('/login', async (req, res, next) => {
  try {
    const { email,password } = req.body;
    if (!email||!password) return res.status(400).json({ message:'Missing credentials' });
    const user = await User.findOne({ email });
    if (!user||!(await bcrypt.compare(password,user.password))) return res.status(401).json({ message:'Invalid creds' });
    const token = jwt.sign({ userId:user._id },JWT_SECRET,{expiresIn:JWT_EXPIRES_IN});
    res.json({ token, expiresIn:JWT_EXPIRES_IN });
  } catch(e){ next(e); }
});

// Analyze: resize, thumbnail, forward
app.post('/analyze', authenticateUser, upload.single('image'), async (req, res, next) => {
  try {
    const { plantType, waterFreq, language } = req.body;
    if (!plantType||!waterFreq||!req.file) return res.status(400).json({ message:'Missing data or file' });

    const filePath = path.join(UPLOAD_DIR, req.file.filename);
    const thumbName = `thumb-${req.file.filename}`;
    const thumbPath = path.join(UPLOAD_DIR, thumbName);
    // Resize max 800px
    const buffer = await sharp(filePath)
      .resize(800,800,{fit:'inside'})
      .jpeg({ quality:80 })
      .toBuffer();
    // Save resized buffer back
    fs.writeFileSync(filePath, buffer);
    // Create thumbnail 200px
    await sharp(buffer)
      .resize(200,200,{fit:'cover'})
      .toFile(thumbPath);

    // Predict
    const predictRes = await axios.post(
      `${FLASK_URL}/predict`, buffer,
      { headers:{ 'Content-Type':'application/octet-stream' }}
    );
    let status='Unknown';
    if(typeof predictRes.data==='string'){
      const m=predictRes.data.match(/Prediction:\s*(\w+)/);
      if(m) status=m[1];
    } else {
      status=predictRes.data.prediction||predictRes.data.status||status;
    }
    // Recommend
    let recommendation='';
    try{
      const rec = await axios.post(`${GEMINI_URL}/recommend`,{ status,plantType,waterFreq:+waterFreq,language });
      recommendation=rec.data.recommendation;
    }catch{ recommendation='Unavailable'; }
    // Save history
    const imageUrl=`/uploads/${req.file.filename}`;
    const thumbnailUrl=`/uploads/${thumbName}`;
    await User.findByIdAndUpdate(req.userId,{ $push:{ history:{ plantType,status,recommendation,imageUrl,thumbnailUrl }} });
    res.json({ prediction:status,recommendation,imageUrl,thumbnailUrl });
  } catch(e){ next(e); }
});

// History with pagination
app.get('/history', authenticateUser, async (req, res, next) => {
  try {
    const page = Math.max(parseInt(req.query.page)||1,1);
    const limit = Math.min(Math.max(parseInt(req.query.limit)||10,1),100);
    const skip=(page-1)*limit;
    const [result]=await User.aggregate([
      { $match:{ _id:mongoose.Types.ObjectId(req.userId) } },
      { $project:{ username:1,total:{ $size:'$history' },history:{$slice:['$history',skip,limit] } }}
    ]);
    if(!result) return res.status(404).json({ message:'User not found' });
    res.json({ username:result.username, history:result.history, page,limit,totalItems:result.total, totalPages:Math.ceil(result.total/limit) });
  }catch(e){ next(e); }
});

// Error handler\ napp.use((err,req,res,next)=>{
  console.error(err);
  res.status(err.status||500).json({ message:err.message||'Error' });
});

// Start
app.listen(PORT,'0.0.0.0',()=>console.log(`🚀 Listening on ${PORT}`));
