import React from "react";
import { useNavigate } from "react-router-dom";

export default function Jobs() {
  const navigate = useNavigate();

  return (
    <>
      <header><h1>Find Your Opportunity</h1></header>
      <nav>
        <a onClick={() => navigate("/")}>Home</a>
        <a onClick={() => navigate("/candidates")}>Candidates</a>
        <a onClick={() => navigate("/recruiters")}>Recruiters</a>
        <a onClick={() => navigate("/collegeadmins")}>College Admins</a>
        <a onClick={() => navigate("/jobs")}>Jobs</a>
        <a onClick={() => navigate("/login")}>Login</a>
      </nav>

      <main className="container">
        <section className="card">
          <h2>Job Listings</h2>
          <div>
            <h3>Software Engineer - ABC Corp</h3>
            <p>Location: Remote | Match Score: 92%</p>
            <button className="btn">Apply Now</button>
          </div>
          <div>
            <h3>Marketing Analyst - XYZ Inc</h3>
            <p>Location: Mumbai | Match Score: 77%</p>
            <button className="btn">Apply Now</button>
          </div>
        </section>
      </main>

      <footer>&copy; 2025 Job Nexus</footer>
    </>
  );
}
