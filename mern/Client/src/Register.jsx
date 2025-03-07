import axios from "axios";
import React, { useState } from "react";
import { FaEnvelope, FaLock, FaTimes, FaUser } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

const Register = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState("");

  // Use the direct video URL as the initial video source
  const [videoSrc, setVideoSrc] = useState(
    "https://videos.pexels.com/video-files/30639174/13113894_360_640_25fps.mp4"
  );

  // Update state on input change
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      // Use your deployed Node server URL on Render
      const response = await axios.post(
        "https://backend-lj86.onrender.com/register",
        formData
      );
      console.log(response.data.message);
      // Redirect to login page after successful registration
      navigate("/login");
    } catch (err) {
      setError(err.response?.data?.message || "Registration failed.");
    }
  };

  return (
    <div className="relative h-screen w-screen overflow-hidden">
      {/* Background Video with fallback support */}
      <video
        autoPlay
        loop
        muted
        className="absolute inset-0 w-full h-full object-cover"
        onError={() =>
          setVideoSrc("https://videos.pexels.com/video-files/30639174/13113894_360_640_25fps.mp4")
        }
      >
        <source src={videoSrc} type="video/mp4" />
        Your browser does not support the video tag.
      </video>

      {/* Dark Overlay for Readability */}
      <div className="absolute inset-0 bg-black opacity-60"></div>

      {/* Form Container */}
      <div className="relative flex items-center justify-center h-full px-4">
        <div className="relative bg-white/20 backdrop-blur-xl p-10 rounded-3xl shadow-2xl max-w-md w-full transition-transform transform hover:scale-105">
          {/* Cross Button inside the card */}
          <button
            onClick={() => navigate(-1)}
            className="absolute top-4 right-4 text-white text-2xl transition-transform duration-300 hover:scale-110"
          >
            <FaTimes />
          </button>

          <h1 className="text-center text-4xl font-bold text-white mb-6">
            Register
          </h1>
          {error && (
            <p className="text-red-500 text-center mb-4 animate-pulse">
              {error}
            </p>
          )}
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Username Field */}
            <div className="relative">
              <span className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-300">
                <FaUser />
              </span>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                placeholder="Username"
                className="w-full pl-12 py-3 rounded-xl bg-white/20 border border-white/30 text-white placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-400 transition-all"
                required
              />
            </div>

            {/* Email Field */}
            <div className="relative">
              <span className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-300">
                <FaEnvelope />
              </span>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="Email Address"
                className="w-full pl-12 py-3 rounded-xl bg-white/20 border border-white/30 text-white placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-400 transition-all"
                required
              />
            </div>

            {/* Password Field */}
            <div className="relative">
              <span className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-300">
                <FaLock />
              </span>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Password"
                className="w-full pl-12 py-3 rounded-xl bg-white/20 border border-white/30 text-white placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-400 transition-all"
                required
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="w-full py-3 rounded-xl bg-blue-500 hover:bg-blue-400 text-white font-semibold transition-all shadow-lg"
            >
              Sign Up
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Register;
