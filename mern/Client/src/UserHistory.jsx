import axios from "axios";
import React, { useEffect, useState } from "react";
import { FaChevronDown, FaChevronUp, FaTimes } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

const UserHistory = ({ onClose }) => {
  const [userHistory, setUserHistory] = useState({ username: "", history: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedItems, setExpandedItems] = useState({});
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [showRedSquare, setShowRedSquare] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchUserHistory = async () => {
      const token = localStorage.getItem("token");
      if (!token) {
        setIsAuthenticated(false);
        setLoading(false);
        return;
      }
      setIsAuthenticated(true);
      try {
        // Change localhost to your machine's IP:
        const response = await axios.get("http://192.168.29.41:5000/history", {
          headers: { Authorization: token },
        });
        setUserHistory(response.data);
      } catch (err) {
        console.error("Error fetching user history:", err);
        setError("Failed to load history. Please try again later.");
      } finally {
        setLoading(false);
      }
    };
    fetchUserHistory();
  }, []);

  const handleLogin = () => {
    navigate("/login");
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  const toggleItem = (index) => {
    setExpandedItems((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  // Handle close click with red square animation before closing
  const handleCloseClick = () => {
    setShowRedSquare(true);
    setTimeout(() => {
      onClose();
    }, 500);
  };

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50">
      {/* Modal Overlay with fade effect */}
      <div
        className="fixed inset-0 bg-black opacity-50 transition-opacity duration-300"
        onClick={onClose}
      ></div>
      <div className="relative bg-white w-full max-w-md mx-4 sm:mx-auto rounded-lg shadow-xl p-4 sm:p-6 z-10 max-h-[80vh] overflow-y-auto transform transition-all duration-300 ease-in-out">
        {/* Close Icon Container */}
        <div className="absolute top-4 right-4">
          {showRedSquare && (
            <div
              className="absolute inset-0 bg-red-500 rounded transition-opacity duration-300"
              style={{ opacity: showRedSquare ? 1 : 0 }}
            ></div>
          )}
          <button
            onClick={handleCloseClick}
            className="relative text-gray-600 hover:text-gray-800 focus:outline-none transition-colors duration-300 z-20"
            aria-label="Close"
          >
            <FaTimes size={20} />
          </button>
        </div>

        <div className="mb-4 border-b pb-2 animate-fadeIn">
          <h3 className="font-bold text-xl sm:text-2xl text-gray-800">
            User History
          </h3>
          {isAuthenticated && (
            <p className="text-sm text-gray-600 mt-1">
              Welcome, {userHistory.username?.trim() || "User"}
            </p>
          )}
        </div>

        {!isAuthenticated ? (
          <div className="text-center animate-fadeIn">
            <p className="text-gray-700 mb-4">
              Please log in to view your history.
            </p>
            <button
              onClick={handleLogin}
              className="bg-blue-600 text-white w-full sm:w-auto px-4 py-2 rounded hover:bg-blue-700 transition-all duration-300"
            >
              Login
            </button>
          </div>
        ) : (
          <>
            <div className="mb-4 flex justify-end animate-fadeIn">
              <button
                onClick={handleLogout}
                className="text-sm text-red-600 hover:underline focus:outline-none transition-colors duration-300"
              >
                Logout
              </button>
            </div>
            {loading ? (
              // Skeleton Loading Effect
              <div className="space-y-4 animate-pulse">
                <div className="h-6 w-1/2 bg-gray-200 rounded"></div>
                <div className="h-4 w-full bg-gray-200 rounded"></div>
                <div className="h-4 w-full bg-gray-200 rounded"></div>
                <div className="h-4 w-full bg-gray-200 rounded"></div>
              </div>
            ) : error ? (
              <div className="p-4 bg-red-100 text-red-700 rounded animate-fadeIn">
                {error}
              </div>
            ) : userHistory.history.length === 0 ? (
              <p className="text-sm text-gray-600 animate-fadeIn">
                No history available.
              </p>
            ) : (
              <ul className="space-y-4 animate-fadeIn">
                {userHistory.history.map((item, index) => {
                  const isExpanded = expandedItems[index] || false;
                  return (
                    <li
                      key={index}
                      className="border rounded-lg p-4 hover:shadow-lg transition-shadow duration-300"
                    >
                      <div
                        className="flex justify-between items-center cursor-pointer"
                        onClick={() => toggleItem(index)}
                      >
                        <span className="font-semibold text-gray-800 transition-colors duration-300">
                          Plant: {item.plantType}
                        </span>
                        <div className="transition-transform duration-300">
                          {isExpanded ? (
                            <FaChevronUp size={16} className="text-gray-600" />
                          ) : (
                            <FaChevronDown
                              size={16}
                              className="text-gray-600"
                            />
                          )}
                        </div>
                      </div>
                      <div
                        className={`mt-3 border-t pt-3 transition-all duration-300 ease-in-out overflow-hidden ${
                          isExpanded
                            ? "max-h-96 opacity-100"
                            : "max-h-0 opacity-0"
                        }`}
                      >
                        <div className="text-gray-600">
                          <strong>Status:</strong> {item.status}
                        </div>
                        <div className="text-gray-600 mt-1">
                          <strong>Recommendation:</strong> {item.recommendation}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          Analyzed: {new Date(item.analyzedAt).toLocaleString()}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default UserHistory;
