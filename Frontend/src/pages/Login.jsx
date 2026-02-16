<<<<<<< HEAD
import React, { useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import "./Login.css";

=======
import React, { useState, useEffect } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import "./Login.css";

//const API_BASE = "http://localhost/JobNexus-main/Backend-PHP/api";

>>>>>>> upstream/main
export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("candidate");
  const [isLogin, setIsLogin] = useState(true);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [loading, setLoading] = useState(false);
<<<<<<< HEAD
  const navigate = useNavigate();
  const location = useLocation();

  // Check if already logged in and redirect
  React.useEffect(() => {
    const loggedIn = localStorage.getItem("loggedIn") === "true";
    const userRole = localStorage.getItem("userRole");

    if (loggedIn && userRole) {
      // User is already logged in, redirect to their dashboard
      switch (userRole) {
        case "candidate":
          navigate("/candidates", { replace: true });
          break;
        case "recruiter":
          navigate("/recruiters", { replace: true });
          break;
        case "admin":
          navigate("/collegeadmins", { replace: true });
          break;
        default:
          break;
      }
    }
  }, [navigate]);

  // Set role from navigation state if provided
  React.useEffect(() => {
=======

  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
>>>>>>> upstream/main
    if (location.state?.role) {
      setRole(location.state.role);
    }
  }, [location]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

<<<<<<< HEAD
    try {
      const endpoint = isLogin ? "login" : "register";
      const url = `http://localhost/JobNexus/Backend-PHP/api/${endpoint}.php`;

      const payload = isLogin
        ? { email, password, role }
        : { email, password, role, firstName, lastName };

      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (data.success) {
=======
    const endpoint = isLogin ? "login.php" : "register.php";
    const url = `http://localhost/JobNexus-main/Backend-PHP/api/${endpoint}`;

    const payload = isLogin
      ? { email, password, role }
      : { email, password, role, firstName, lastName };

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      // Handle HTTP-level errors clearly
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      const data = await response.json();

      // LOGIN SUCCESS
      if (isLogin && data.success) {
>>>>>>> upstream/main
        localStorage.setItem("loggedIn", "true");
        localStorage.setItem("user", JSON.stringify(data.user));
        localStorage.setItem("token", data.token);
        localStorage.setItem("userRole", data.user.role);

<<<<<<< HEAD
        // Redirect based on role
=======
>>>>>>> upstream/main
        switch (data.user.role) {
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
<<<<<<< HEAD
      } else {
        alert(data.message || "Authentication failed");
      }
    } catch (error) {
      console.error("Login error:", error);
      alert("Unable to connect to server. Make sure XAMPP is running.");
=======
        return;
      }

      // REGISTER SUCCESS
      if (!isLogin && data.success) {
        alert("Registration successful! Please sign in.");
        setIsLogin(true);
        setPassword("");
        return;
      }

      // BACKEND-REPORTED ERROR
      alert(data.message || "Authentication failed");

    } catch (error) {
      console.error("Auth request failed:", error);
      alert("Unable to reach server. Please try again.");
>>>>>>> upstream/main
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page-compact">
      <div className="back-home">
<<<<<<< HEAD
        <Link to="/home" className="back-link">← Back to Home</Link>
=======
        <Link to="/" className="back-link">← Back to Home</Link>
>>>>>>> upstream/main
      </div>

      <div className="login-container-compact">
        <div className="brand-compact">
          <h1 className="logo-compact">
            <span className="logo-gradient">Job</span>Nexus
          </h1>
          <p className="tagline-compact">
<<<<<<< HEAD
            {isLogin ? "Welcome back! Sign in to continue" : "Join our community today"}
          </p>
        </div>

        <div className="form-card-compact">
          <div className="form-header-compact">
            <h2>{isLogin ? "Sign In" : "Create Account"}</h2>
            <button
              type="button"
              className="toggle-form-btn"
              onClick={() => setIsLogin(!isLogin)}
            >
              {isLogin ? "Need an account? Sign up" : "Have an account? Sign in"}
            </button>
          </div>

          <div className="role-selection-compact inside-form">
            <div className="role-tabs-compact">
              <button
                className={`role-tab-compact ${role === "candidate" ? "active" : ""}`}
                onClick={() => setRole("candidate")}
                type="button"
              >
                👤 Candidate
              </button>

              <button
                className={`role-tab-compact ${role === "recruiter" ? "active" : ""}`}
                onClick={() => setRole("recruiter")}
                type="button"
              >
                💼 Recruiter
              </button>

              <button
                className={`role-tab-compact ${role === "admin" ? "active" : ""}`}
                onClick={() => setRole("admin")}
                type="button"
              >
                🏛️ Admin
              </button>
            </div>

            <div className="role-description-compact">
              {role === "candidate" && "Find jobs, build your resume, and get AI-powered career guidance"}
              {role === "recruiter" && "Post jobs, find candidates, and streamline your hiring process"}
              {role === "admin" && "Manage student placements and connect with recruiters"}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="form-compact">
            {!isLogin && (
              <div className="name-fields-compact">
                <div className="form-group-compact">
                  <input
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    placeholder="First name"
                    required
                  />
                </div>

                <div className="form-group-compact">
                  <input
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    placeholder="Last name"
                    required
                  />
                </div>
              </div>
            )}

            <div className="form-group-compact">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email address"
                required
              />
            </div>

            <div className="form-group-compact">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                minLength="6"
                required
              />
              {!isLogin && (
                <p className="password-hint-compact">
                  Must be at least 6 characters
                </p>
              )}
            </div>

            {isLogin && (
              <div className="forgot-password-compact">
                <Link to="/forgot-password" className="forgot-link-compact">
                  Forgot password?
                </Link>
              </div>
            )}

            <button
              type="submit"
              className="submit-btn-compact"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner-compact"></span>
                  {isLogin ? "Signing in..." : "Creating account..."}
                </>
              ) : (
                isLogin ? "Sign In" : "Create Account"
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
=======
            {isLogin
              ? "Welcome back! Sign in to continue"
              : "Join our community today"}
          </p>
        </div>

        {/* ROLE TABS */}
        <div className="role-tabs-compact">
          {["candidate", "recruiter", "admin"].map((r) => (
            <button
              key={r}
              type="button"
              className={`role-tab-compact ${role === r ? "active" : ""}`}
              onClick={() => setRole(r)}
            >
              {r.charAt(0).toUpperCase() + r.slice(1)}
            </button>
          ))}
        </div>

        {/* FORM */}
        <form onSubmit={handleSubmit} className="form-compact">
          {!isLogin && (
            <>
              <input
                placeholder="First Name"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
              />
              <input
                placeholder="Last Name"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
              />
            </>
          )}

          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <input
            type="password"
            placeholder="Password"
            minLength="6"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <button type="submit" disabled={loading}>
            {loading
              ? "Please wait..."
              : isLogin
              ? "Sign In"
              : "Create Account"}
          </button>

          <p
            className="toggle-form-btn"
            onClick={() => setIsLogin(!isLogin)}
          >
            {isLogin
              ? "Need an account? Sign up"
              : "Have an account? Sign in"}
          </p>
        </form>
      </div>
    </div>
  );
}
>>>>>>> upstream/main
