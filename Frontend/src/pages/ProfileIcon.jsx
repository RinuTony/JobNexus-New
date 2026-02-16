import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import "./ProfileIcon.css";

export default function ProfileIcon() {
  const [user, setUser] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef(null);
  const buttonRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Load user data from localStorage
    const userData = localStorage.getItem("user");
    console.log("User data from localStorage:", userData);
    if (userData) {
      try {
        setUser(JSON.parse(userData));
      } catch (error) {
        console.error("Error parsing user data:", error);
      }
    }
    
    // Close dropdown when clicking outside
    const handleClickOutside = (event) => {
      console.log("Click detected, showDropdown:", showDropdown);
      console.log("Clicked element:", event.target);
      console.log("Dropdown ref:", dropdownRef.current);
      console.log("Button ref:", buttonRef.current);
      
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        console.log("Click outside dropdown, closing");
        setShowDropdown(false);
      }
    };
    
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showDropdown]);

  const handleButtonClick = (e) => {
    console.log("Profile button clicked!");
    console.log("Event target:", e.target);
    console.log("Current showDropdown:", showDropdown);
    e.stopPropagation(); // Prevent event bubbling
    setShowDropdown(prev => !prev);
  };

  const handleLogout = () => {
    localStorage.clear();
    navigate("/login");
  };

  const getInitials = () => {
    if (user?.firstName && user?.lastName) {
      return `${user.firstName.charAt(0)}${user.lastName.charAt(0)}`.toUpperCase();
    }
    if (user?.email) {
      return user.email.charAt(0).toUpperCase();
    }
    return "U";
  };

  const getAvatarColor = () => {
    if (!user?.email) return "#4f46e5";
    
    const colors = [
      "#4f46e5", // Indigo
      "#059669", // Emerald
      "#dc2626", // Red
      "#d97706", // Amber
      "#7c3aed", // Violet
      "#0891b2", // Cyan
    ];
    
    const hash = user.email.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return colors[hash % colors.length];
  };

  const handleMenuItemClick = (path) => {
    console.log("Navigating to:", path);
    setShowDropdown(false);
    navigate(path);
  };

  return (
    <div className="profile-icon-container" ref={dropdownRef}>
      <button 
        ref={buttonRef}
        className="profile-icon-button"
        onClick={handleButtonClick}
        aria-label="User profile"
      >
        {user?.avatarUrl ? (
          <img 
            src={user.avatarUrl} 
            alt="Profile" 
            className="profile-avatar"
          />
        ) : (
          <div 
            className="profile-initials" 
            style={{ backgroundColor: getAvatarColor() }}
          >
            {getInitials()}
          </div>
        )}
        <span className="profile-name">
          {user?.firstName || user?.email?.split("@")[0] || "User"}
        </span>
        <svg 
          className={`dropdown-arrow ${showDropdown ? "open" : ""}`} 
          width="16" 
          height="16" 
          viewBox="0 0 24 24"
        >
          <path fill="currentColor" d="M7 10l5 5 5-5z" />
        </svg>
      </button>

      {showDropdown && (
        <div className="profile-dropdown" style={{ display: 'block' }}>
          <div className="dropdown-header">
            <div className="dropdown-avatar">
              {user?.avatarUrl ? (
                <img src={user.avatarUrl} alt="Profile" />
              ) : (
                <div style={{ backgroundColor: getAvatarColor() }}>
                  {getInitials()}
                </div>
              )}
            </div>
            <div className="dropdown-user-info">
              <h4>{user?.firstName && user?.lastName ? `${user.firstName} ${user.lastName}` : user?.email}</h4>
              <p className="user-email">{user?.email}</p>
              <p className="user-role">
                {user?.role === "candidate" && "👤 Candidate"}
                {user?.role === "recruiter" && "💼 Recruiter"}
                {user?.role === "admin" && "🏛️ College Admin"}
              </p>
            </div>
          </div>

          <div className="dropdown-divider"></div>

          <div className="dropdown-menu">
            <button 
              className="dropdown-item"
              onClick={() => handleMenuItemClick("/profile")}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M12 12C14.21 12 16 10.21 16 8C16 5.79 14.21 4 12 4C9.79 4 8 5.79 8 8C8 10.21 9.79 12 12 12ZM12 14C9.33 14 4 15.34 4 18V20H20V18C20 15.34 14.67 14 12 14Z" fill="currentColor"/>
              </svg>
              <span>My Profile</span>
            </button>

<<<<<<< HEAD
=======
            <button 
              className="dropdown-item"
              onClick={() => handleMenuItemClick("/settings")}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M19.14 12.94C19.18 12.63 19.2 12.32 19.2 12C19.2 11.68 19.18 11.37 19.14 11.06L21.16 9.12C21.35 8.94 21.38 8.65 21.24 8.44L19.36 5.72C19.23 5.53 19 5.45 18.8 5.51L16.34 6.3C15.88 5.95 15.38 5.66 14.85 5.45L14.47 2.85C14.45 2.63 14.27 2.46 14.05 2.46H9.95C9.73 2.46 9.55 2.63 9.53 2.85L9.15 5.45C8.62 5.66 8.12 5.95 7.66 6.3L5.2 5.51C5 5.45 4.77 5.53 4.64 5.72L2.76 8.44C2.62 8.65 2.65 8.94 2.84 9.12L4.86 11.06C4.82 11.37 4.8 11.68 4.8 12C4.8 12.32 4.82 12.63 4.86 12.94L2.84 14.88C2.65 15.06 2.62 15.35 2.76 15.56L4.64 18.28C4.77 18.47 5 18.55 5.2 18.49L7.66 17.7C8.12 18.05 8.62 18.34 9.15 18.55L9.53 21.15C9.55 21.37 9.73 21.54 9.95 21.54H14.05C14.27 21.54 14.45 21.37 14.47 21.15L14.85 18.55C15.38 18.34 15.88 18.05 16.34 17.7L18.8 18.49C19 18.55 19.23 18.47 19.36 18.28L21.24 15.56C21.38 15.35 21.35 15.06 21.16 14.88L19.14 12.94ZM12 15.6C10.29 15.6 8.9 14.21 8.9 12.5C8.9 10.79 10.29 9.4 12 9.4C13.71 9.4 15.1 10.79 15.1 12.5C15.1 14.21 13.71 15.6 12 15.6Z" fill="currentColor"/>
              </svg>
              <span>Settings</span>
            </button>

            {user?.role === "candidate" && (
              <button 
                className="dropdown-item"
                onClick={() => handleMenuItemClick("/my-resume")}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <path d="M14 2H6C4.9 2 4.01 2.9 4.01 4L4 20C4 21.1 4.89 22 5.99 22H18C19.1 22 20 21.1 20 20V8L14 2ZM16 18H8V16H16V18ZM16 14H8V12H16V14ZM13 9V3.5L18.5 9H13Z" fill="currentColor"/>
                </svg>
                <span>My Resume</span>
              </button>
            )}

>>>>>>> upstream/main
            {user?.role === "recruiter" && (
              <button 
                className="dropdown-item"
                onClick={() => handleMenuItemClick("/my-jobs")}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <path d="M20 6H16V4C16 2.89 15.11 2 14 2H10C8.89 2 8 2.89 8 4V6H4C2.89 6 2.01 6.89 2.01 8L2 19C2 20.11 2.89 21 4 21H20C21.11 21 22 20.11 22 19V8C22 6.89 21.11 6 20 6ZM10 4H14V6H10V4ZM20 19H4V8H20V19Z" fill="currentColor"/>
                </svg>
                <span>My Jobs</span>
              </button>
            )}

            <div className="dropdown-divider"></div>

            <button 
              className="dropdown-item logout"
              onClick={handleLogout}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M17 7L15.59 8.41L18.17 11H8V13H18.17L15.59 15.58L17 17L22 12L17 7ZM4 5H12V3H4C2.9 3 2 3.9 2 5V19C2 20.1 2.9 21 4 21H12V19H4V5Z" fill="currentColor"/>
              </svg>
              <span>Log Out</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
<<<<<<< HEAD
}
=======
}
>>>>>>> upstream/main
