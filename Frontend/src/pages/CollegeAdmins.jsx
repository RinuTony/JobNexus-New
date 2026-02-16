import React from "react";
import { useNavigate } from "react-router-dom";

export default function CollegeAdmins() {
  const navigate = useNavigate();

<<<<<<< HEAD
  const handleLogout = () => {
    // Add your logout logic here
    localStorage.removeItem("authToken");
    localStorage.removeItem("userRole");
    sessionStorage.clear();
    navigate("/login");
  };

  return (
    <>
      <header><h1>College Admin Dashboard</h1></header>
      
=======
  return (
    <>
      <header><h1>College Admin Dashboard</h1></header>
>>>>>>> upstream/main
      <nav>
        <a onClick={() => navigate("/")}>Home</a>
        <a onClick={() => navigate("/candidates")}>Candidates</a>
        <a onClick={() => navigate("/recruiters")}>Recruiters</a>
        <a onClick={() => navigate("/collegeadmins")}>College Admins</a>
        <a onClick={() => navigate("/jobs")}>Jobs</a>
<<<<<<< HEAD
        <a onClick={() => navigate("/profile")}>Profile</a>
        <a 
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
=======
        <a onClick={() => navigate("/login")}>Login</a>
>>>>>>> upstream/main
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
<<<<<<< HEAD
}
=======
}
>>>>>>> upstream/main
