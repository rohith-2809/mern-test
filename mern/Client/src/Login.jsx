import axios from "axios";
import React, { useState } from "react";
import {
  FaApple,
  FaEnvelope,
  FaEye,
  FaEyeSlash,
  FaLock,
  FaTimes,
  FaUserPlus,
} from "react-icons/fa";
import { useNavigate } from "react-router-dom";
import backgroundVideo from "./assets/3179187-hd_1920_1080_24fps.mp4";

const Login = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const submitHandler = async (e) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      // Replace this IP with your computer's IP if needed
      const response = await axios.post("http://192.168.29.41:5000/login", {
        email,
        password,
      });

      if (response.data.token) {
        localStorage.setItem("token", response.data.token);
        navigate("/analyze");
      } else {
        throw new Error("Token not received from server.");
      }
    } catch (err) {
      console.error("Login error:", err);
      setError(err.response?.data?.message || "Login failed.");
    } finally {
      setIsLoading(false);
      setEmail("");
      setPassword("");
    }
  };

  return (
    <div className="relative h-screen w-screen overflow-hidden">
      {/* Background Video */}
      <video
        autoPlay
        loop
        muted
        className="absolute inset-0 w-full h-full object-cover pointer-events-none"
      >
        <source src={backgroundVideo} type="video/mp4" />
      </video>

      {/* Dark Overlay */}
      <div className="absolute inset-0 bg-black/60"></div>

      {/* Centered Login Card */}
      <div className="flex h-full w-full items-center justify-center px-4">
        <div className="relative bg-white/20 backdrop-blur-2xl border border-white/30 shadow-2xl p-10 rounded-3xl max-w-md w-full transition-all duration-300 animate-fadeIn">
          {/* Close Button */}
          <button
            onClick={() => navigate(-1)}
            className="absolute top-4 right-4 text-white text-2xl transition-transform duration-300 hover:scale-110"
          >
            <FaTimes />
          </button>

          <h1 className="text-white font-sans font-extrabold text-4xl text-center mb-2">
            Welcome Back
          </h1>
          <p className="text-gray-300 text-center mb-6">
            Sign in to access your account
          </p>
          {error && (
            <p className="text-red-500 text-center mb-4 animate-pulse">
              {error}
            </p>
          )}

          <form onSubmit={submitHandler} className="flex flex-col space-y-5">
            {/* Email Input */}
            <div className="relative">
              <span className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-300">
                <FaEnvelope />
              </span>
              <input
                type="email"
                placeholder="Email Address"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-12 py-3 rounded-xl bg-white/10 border border-white/30 text-white placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-400 transition-all"
              />
            </div>

            {/* Password Input */}
            <div className="relative">
              <span className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-300">
                <FaLock />
              </span>
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-12 py-3 rounded-xl bg-white/10 border border-white/30 text-white placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-400 transition-all"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-300 hover:text-white transition-all duration-300"
              >
                {showPassword ? <FaEyeSlash /> : <FaEye />}
              </button>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className={`w-full py-3 rounded-xl font-semibold transition-all duration-300 shadow-lg ${
                isLoading
                  ? "bg-gray-500 cursor-not-allowed"
                  : "bg-blue-500 hover:bg-blue-400 text-white"
              }`}
            >
              {isLoading ? "Logging In..." : "Sign In"}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center my-4">
            <div className="flex-grow border-t border-white/20"></div>
            <span className="px-3 text-gray-300">or</span>
            <div className="flex-grow border-t border-white/20"></div>
          </div>

          {/* Social Login Buttons */}
          <div className="flex flex-col space-y-3">
            <button className="w-full flex items-center justify-center bg-white text-black font-semibold py-3 rounded-xl shadow-md hover:bg-gray-100 transition-all duration-300">
              <FaEnvelope className="mr-2" /> Continue with Email
            </button>
            <button className="w-full flex items-center justify-center bg-black text-white font-semibold py-3 rounded-xl shadow-md hover:bg-gray-900 transition-all duration-300">
              <FaApple className="mr-2" /> Continue with Apple
            </button>
          </div>

          {/* Sign Up Button */}
          <div className="flex justify-center mt-6">
            <button
              onClick={() => navigate("/register")}
              className="flex items-center justify-center bg-green-500 hover:bg-green-400 text-white font-semibold py-2 px-4 rounded-full transition-all duration-300 shadow-lg"
            >
              <FaUserPlus className="mr-2 text-xl" /> New User? Sign Up
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
