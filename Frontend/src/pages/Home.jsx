import React from "react";
import { useNavigate } from "react-router-dom";
import ProfileIcon from "./ProfileIcon";
import "./Home.css";

export default function Home() {
  const navigate = useNavigate();
  const loggedIn = localStorage.getItem("loggedIn") === "true";
  const userRole = localStorage.getItem("userRole");

  const handleNavigation = (path) => {
    if (loggedIn) {
<<<<<<< HEAD
=======
      // Check if user has access to the requested path based on their role
>>>>>>> upstream/main
      const roleAccessMap = {
        "/candidates": ["candidate"],
        "/recruiters": ["recruiter"],
        "/collegeadmins": ["admin"],
<<<<<<< HEAD
        "/jobs": ["candidate", "recruiter", "admin"],
      };

      if (roleAccessMap[path]) {
        if (!roleAccessMap[path].includes(userRole)) {
          alert(`Access denied. This section is for ${roleAccessMap[path].join('/')} only.`);
          
=======
        "/jobs": ["candidate", "recruiter", "admin"], // All roles can access jobs
      };

      // If path has specific role requirements
      if (roleAccessMap[path]) {
        if (!roleAccessMap[path].includes(userRole)) {
          // User doesn't have access - redirect to their dashboard
          alert(`Access denied. This section is for ${roleAccessMap[path].join('/')} only.`);
          
          // Redirect to user's appropriate dashboard
>>>>>>> upstream/main
          switch (userRole) {
            case "candidate":
              navigate("/candidates");
              break;
            case "recruiter":
              navigate("/recruiters");
              break;
            case "admin":
              navigate("/collegeadmins");
              break;
            default:
              navigate("/");
          }
          return;
        }
      }
      
<<<<<<< HEAD
      navigate(path);
    } else {
=======
      // User has access, navigate to path
      navigate(path);
    } else {
      // Not logged in - navigate to login with intended path
>>>>>>> upstream/main
      navigate("/login", { state: { intendedPath: path } });
    }
  };

<<<<<<< HEAD
  const handleRoleBasedNavigation = (role) => {
    if (loggedIn) {
      if (userRole === role) {
=======
  const handleDirectNavigation = (path) => {
    navigate(path);
  };

  const handleRoleBasedNavigation = (role) => {
    if (loggedIn) {
      // If already logged in, check if user is trying to access their own role
      if (userRole === role) {
        // Navigate to their dashboard
>>>>>>> upstream/main
        switch (role) {
          case "candidate":
            navigate("/candidates");
            break;
          case "recruiter":
            navigate("/recruiters");
            break;
          case "admin":
            navigate("/collegeadmins");
            break;
        }
      } else {
<<<<<<< HEAD
        alert(`You are currently logged in as a ${userRole}. Please logout to access ${role} features.`);
      }
    } else {
=======
        // User is logged in but trying to access different role
        alert(`You are currently logged in as a ${userRole}. Please logout to access ${role} features.`);
      }
    } else {
      // Not logged in - go to login with selected role
>>>>>>> upstream/main
      navigate("/login", { state: { role } });
    }
  };

  return (
    <>
      <header style={{ position: "relative" }}>
        <div style={{ 
          display: "flex", 
          justifyContent: "space-between", 
          alignItems: "center",
          maxWidth: "1200px",
          margin: "0 auto",
          padding: "0 2rem"
        }}>
          <div>
            <h1>Job Nexus</h1>
            <p>Connecting Candidates, Recruiters, and College Admins for Smarter Careers</p>
          </div>
          
<<<<<<< HEAD
          {loggedIn && (
            <div className="profile-icon-wrapper">
              <ProfileIcon />
            </div>
          )}
        </div>
      </header>

=======
          {/* Profile Icon in top right corner */}
        
      {loggedIn && (
  <div className="profile-icon-wrapper">
    <ProfileIcon />
  </div>
)}
        </div>
        
        {/* Stars */}
        <span className="star" style={{ left: "10%", top: "30px" }}></span>
        <span className="star" style={{ left: "80%", top: "60px", background: "#43e97b" }}></span>
        <span className="star" style={{ left: "50%", top: "20px", background: "#ffae00" }}></span>
      </header>

      {/* No navigation bar - completely removed */}

>>>>>>> upstream/main
      <main className="container">
        <div className="card-row">
          <div className="card">
            <span className="role-badge candidate">Candidate</span>
            <h2>Career Analysis</h2>
            <ul>
              <li>Upload or build your resume with smart recommendations</li>
              <li>Get detailed feedback and improvement tips</li>
              <li>See skill gaps and possible career paths</li>
              <li>One-click job applications & match score view</li>
              <li>Personalized course recommendations</li>
            </ul>
            <button 
              className="btn" 
              onClick={() => handleRoleBasedNavigation("candidate")}
            >
              {loggedIn && userRole === "candidate" 
                ? "Go to Dashboard" 
                : loggedIn 
                  ? "Switch to Candidate" 
                  : "Explore as Candidate"
              }
            </button>
          </div>

          <div className="card">
            <span className="role-badge recruiter">Recruiter</span>
            <h2>Smart Hiring</h2>
            <ul>
              <li>Upload & enhance job descriptions with AI</li>
              <li>Post jobs and connect with college admins</li>
              <li>Bulk resume analysis, ranking, and shortlisting</li>
              <li>Direct communication with matched candidates</li>
            </ul>
            <button 
              className="btn recruiter" 
              onClick={() => handleRoleBasedNavigation("recruiter")}
            >
              {loggedIn && userRole === "recruiter" 
                ? "Go to Dashboard" 
                : loggedIn 
                  ? "Switch to Recruiter" 
                  : "Join as Recruiter"
              }
            </button>
          </div>

          <div className="card">
            <span className="role-badge admin">College Admin</span>
            <h2>Campus Connect</h2>
            <ul>
              <li>Bulk upload student resumes</li>
              <li>Match requirement of recruiters</li>
              <li>Track application and hiring status</li>
              <li>Build bridges between talent & opportunity</li>
            </ul>
            <button 
              className="btn admin" 
              onClick={() => handleRoleBasedNavigation("admin")}
            >
              {loggedIn && userRole === "admin" 
                ? "Go to Dashboard" 
                : loggedIn 
                  ? "Switch to Admin" 
                  : "Onboard as Admin"
              }
            </button>
          </div>
        </div>

<<<<<<< HEAD
=======
        {/* Additional info for logged-in users */}
>>>>>>> upstream/main
        {loggedIn && (
          <div className="user-status-card" style={{
            marginTop: "2rem",
            padding: "1.5rem",
            background: "#f0f9ff",
            border: "1px solid #bae6fd",
            borderRadius: "12px",
            textAlign: "center"
          }}>
            <p style={{ margin: 0, color: "#0369a1", fontWeight: "500" }}>
              👋 Welcome back! You are logged in as a <strong>{userRole}</strong>.
              {userRole === "candidate" && " Explore job opportunities and enhance your career."}
              {userRole === "recruiter" && " Find the perfect candidates for your organization."}
              {userRole === "admin" && " Manage student placements and connect with recruiters."}
            </p>
            <div style={{ marginTop: "1rem", display: "flex", gap: "10px", justifyContent: "center" }}>
              <button 
                onClick={() => navigate("/profile")}
                style={{
                  padding: "0.5rem 1rem",
                  background: "transparent",
                  border: "1px solid #0369a1",
                  color: "#0369a1",
                  borderRadius: "6px",
                  cursor: "pointer"
                }}
              >
                View Profile
              </button>
              <button 
                onClick={() => {
                  localStorage.clear();
<<<<<<< HEAD
                  navigate("/login");
=======
                  navigate("/");
>>>>>>> upstream/main
                  window.location.reload();
                }}
                style={{
                  padding: "0.5rem 1rem",
                  background: "#fef2f2",
                  border: "1px solid #dc2626",
                  color: "#dc2626",
                  borderRadius: "6px",
                  cursor: "pointer"
                }}
              >
                Logout
              </button>
            </div>
          </div>
        )}

<<<<<<< HEAD
=======
        {/* For non-logged in users, show login button */}
>>>>>>> upstream/main
        {!loggedIn && (
          <div className="login-prompt" style={{
            marginTop: "3rem",
            textAlign: "center",
            padding: "2rem",
            background: "linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)",
            borderRadius: "12px",
            border: "1px solid #e2e8f0"
          }}>
            <h3 style={{ marginBottom: "1rem", color: "#1e293b" }}>Ready to Get Started?</h3>
            <p style={{ marginBottom: "1.5rem", color: "#64748b" }}>
              Join thousands of candidates, recruiters, and college admins who are transforming careers and hiring.
            </p>
            <button 
              onClick={() => navigate("/login")}
              style={{
                padding: "0.75rem 2rem",
                background: "#4f46e5",
                color: "white",
                border: "none",
                borderRadius: "8px",
                fontSize: "1rem",
                fontWeight: "600",
                cursor: "pointer",
                transition: "all 0.3s ease"
              }}
              onMouseOver={(e) => e.target.style.background = "#4338ca"}
              onMouseOut={(e) => e.target.style.background = "#4f46e5"}
            >
              Sign In / Create Account
            </button>
          </div>
        )}
      </main>

<<<<<<< HEAD
      <footer>&copy; 2025 Job Nexus – Built for careers, powered by you!</footer>
=======
      <footer>&copy; 2025 Job Nexus — Built for careers, powered by you!</footer>
>>>>>>> upstream/main
    </>
  );
}