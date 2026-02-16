// App.js - Fixed version with smart initial routing
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { useEffect, useState } from "react";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Candidates from "./pages/Candidates";
import Recruiters from "./pages/Recruiters";
import CollegeAdmins from "./pages/CollegeAdmins";
import Profile from "./pages/Profile";
import InterviewPrep from "./pages/InterviewPrep";
import MatchScore from "./pages/MatchScore";
import ResumeRanking from "./pages/ResumeRanking";
import Settings from "./pages/Settings";
import JobListings from './pages/JobListings';
import ProtectedRoute from "./components/ProtectedRoute";
import ResumeBuilder from "./pages/ResumeBuilder";
import ResumePreview from './pages/ResumePreview';

// Component to handle initial redirect
function InitialRedirect() {
  const [redirect, setRedirect] = useState(null);

  useEffect(() => {
    const loggedIn = localStorage.getItem("loggedIn") === "true";
    const userRole = localStorage.getItem("userRole");

    if (loggedIn && userRole) {
      // User is logged in, redirect to their dashboard
      switch (userRole) {
        case "candidate":
          setRedirect("/candidates");
          break;
        case "recruiter":
          setRedirect("/recruiters");
          break;
        case "admin":
          setRedirect("/collegeadmins");
          break;
        default:
          setRedirect("/login");
      }
    } else {
      // User is not logged in, redirect to login
      setRedirect("/login");
    }
  }, []);

  if (redirect) {
    return <Navigate to={redirect} replace />;
  }

  return null; // or a loading spinner
}

function App() {
  return (
    <Router>
      <Routes>
        {/* Root route - smart redirect */}
        <Route path="/" element={<InitialRedirect />} />
        
        {/* Public Routes */}
        <Route path="/home" element={<Home />} />
        <Route path="/login" element={<Login />} />
        
        {/* Candidate Routes */}
        <Route element={<ProtectedRoute allowedRoles={["candidate"]} />}>
          <Route path="/candidates" element={<Candidates />} />
          <Route path="/match-score" element={<MatchScore />} />
          <Route path="/interview-prep" element={<InterviewPrep />} />
          <Route path="/resume-builder" element={<ResumeBuilder />} />
          <Route path="/resume-preview" element={<ResumePreview />} />
        </Route>
        
        {/* Recruiter Routes */}
        <Route element={<ProtectedRoute allowedRoles={["recruiter"]} />}>
          <Route path="/recruiters" element={<Recruiters />} />
          <Route path="/rank-candidates" element={<ResumeRanking />} />
        </Route>
        
        {/* Admin Routes */}
        <Route element={<ProtectedRoute allowedRoles={["admin"]} />}>
          <Route path="/collegeadmins" element={<CollegeAdmins />} />
        </Route>
        
        {/* Shared Routes (all logged-in users) */}
        <Route element={<ProtectedRoute allowedRoles={["candidate", "recruiter", "admin"]} />}>
          <Route path="/profile" element={<Profile />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/jobs" element={<JobListings />} />
        </Route>
        
        {/* Fallback Routes */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
