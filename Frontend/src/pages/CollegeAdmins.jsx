import React from "react";
import { useNavigate } from "react-router-dom";

export default function CollegeAdmins() {
  const navigate = useNavigate();

  const handleLogout = (e) => {
    e.preventDefault();
    // Add your logout logic here
    localStorage.removeItem("authToken");
    localStorage.removeItem("userRole");
    sessionStorage.clear();
    navigate("/login");
  };

  return (
    <>
      <header><h1>College Admin Dashboard</h1></header>
      
      <nav>
        <a href="/" onClick={(e) => { e.preventDefault(); navigate("/"); }}>Home</a>
        <a href="/candidates" onClick={(e) => { e.preventDefault(); navigate("/candidates"); }}>Candidates</a>
        <a href="/recruiters" onClick={(e) => { e.preventDefault(); navigate("/recruiters"); }}>Recruiters</a>
        <a href="/collegeadmins" onClick={(e) => { e.preventDefault(); navigate("/collegeadmins"); }}>College Admins</a>
        <a href="/jobs" onClick={(e) => { e.preventDefault(); navigate("/jobs"); }}>Jobs</a>
        <a href="/profile" onClick={(e) => { e.preventDefault(); navigate("/profile"); }}>Profile</a>
        <a 
          href="/login"
          onClick={handleLogout}
          style={{
            marginLeft: "auto",
            color: "#dc3545",
            fontWeight: "bold",
            cursor: "pointer"
          }}
        >
          Logout
        </a>
      </nav>

      <main className="container">
        <section className="card">
          <h2>Bulk Upload Student Resumes</h2>
          <form>
            <label>Select Resume Files:</label>
            <input type="file" multiple />
            <button className="btn">Upload</button>
          </form>
        </section>

        <section className="card">
          <h2>Manage Recruiter Connections</h2>
          <ul>
            <li>View recruiter requests</li>
            <li>Approve or assign student applications</li>
          </ul>
        </section>

        <section className="card">
          <h2>Track Status</h2>
          <ul>
            <li>Monitor hiring process and student application status</li>
          </ul>
        </section>
      </main>

      <footer>&copy; 2025 Job Nexus</footer>
    </>
  );
}
