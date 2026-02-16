<<<<<<< HEAD
import React, { useEffect, useMemo, useState } from "react";
import ProfileIcon from "./ProfileIcon";
import "./Recruiters.css";

export default function Recruiters() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [applications, setApplications] = useState([]);
  const [applicationsLoading, setApplicationsLoading] = useState(false);
  const [applicationsError, setApplicationsError] = useState("");
  const [selectedResume, setSelectedResume] = useState(null);
  const [resumeModalOpen, setResumeModalOpen] = useState(false);
  const [statusUpdates, setStatusUpdates] = useState({});

  const [selectedJobForRanking, setSelectedJobForRanking] = useState("");
  const [rankings, setRankings] = useState([]);
  const [rankingOpen, setRankingOpen] = useState(false);
  const [rankingLoading, setRankingLoading] = useState(false);
  const [rankingError, setRankingError] = useState("");
  const [recruiterJobs, setRecruiterJobs] = useState([]);
  const [selectedStatusFilter, setSelectedStatusFilter] = useState("all");
  const [notifications, setNotifications] = useState([]);
  const [notificationsLoading, setNotificationsLoading] = useState(false);
  const [notificationsError, setNotificationsError] = useState("");

  const API_BASE = "http://localhost/JobNexus/Backend-PHP/api";

  // Fetch applicants and recruiter's jobs
  useEffect(() => {
    const user = JSON.parse(localStorage.getItem("user"));
=======
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Recruiters() {
  const navigate = useNavigate();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);

  const handlePostJob = async (e) => {
    e.preventDefault();

    const user = JSON.parse(localStorage.getItem("user"));

>>>>>>> upstream/main
    if (!user || user.role !== "recruiter") {
      alert("Please login as recruiter");
      return;
    }

<<<<<<< HEAD
    setApplicationsLoading(true);
    setApplicationsError("");
    fetch(`${API_BASE}/get-applicants.php?recruiter_id=${user.id}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          setApplications(data.applications || []);
          const initialStatuses = {};
          data.applications?.forEach((app) => {
            initialStatuses[app.application_id] = app.status;
          });
          setStatusUpdates(initialStatuses);
        } else {
          setApplicationsError(data.message || "Failed to load applications");
        }
      })
      .catch(() => setApplicationsError("Error loading applications"))
      .finally(() => setApplicationsLoading(false));

    fetch(`${API_BASE}/recruiter-jobs.php?recruiter_id=${user.id}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          setRecruiterJobs(data.jobs || []);
        }
      })
      .catch((err) => console.error("Error fetching jobs:", err));

    setNotificationsLoading(true);
    setNotificationsError("");
    fetch(`${API_BASE}/get-notifications.php?user_id=${user.id}&limit=50`)
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          setNotifications(data.notifications || []);
        } else {
          setNotificationsError(data.message || "Failed to load notifications");
        }
      })
      .catch(() => setNotificationsError("Failed to load notifications"))
      .finally(() => setNotificationsLoading(false));
  }, []);

  // Post job
  const handlePostJob = async (e) => {
    e.preventDefault();
    const user = JSON.parse(localStorage.getItem("user"));

    if (!user || user.role !== "recruiter") {
      alert("Please login as recruiter");
=======
    if (!title || !description) {
      alert("Please fill all fields");
>>>>>>> upstream/main
      return;
    }

    setLoading(true);

    try {
<<<<<<< HEAD
      const response = await fetch(`${API_BASE}/post-job.php`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          description,
          recruiter_id: user.id,
        }),
      });
=======
      const response = await fetch(
        "http://localhost/JobNexus-main/Backend-PHP/api/post-job.php",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            title,
            description,
            recruiter_id: user.id
          })
        }
      );
>>>>>>> upstream/main

      const data = await response.json();

      if (data.success) {
        alert("Job posted successfully");
        setTitle("");
        setDescription("");
<<<<<<< HEAD
        fetch(`${API_BASE}/recruiter-jobs.php?recruiter_id=${user.id}`)
          .then((res) => res.json())
          .then((jobsData) => {
            if (jobsData.success) {
              setRecruiterJobs(jobsData.jobs || []);
            }
          });
=======
>>>>>>> upstream/main
      } else {
        alert(data.message || "Failed to post job");
      }
    } catch (error) {
      console.error(error);
<<<<<<< HEAD
      alert("Server error");
=======
      alert("Server error. Try again.");
>>>>>>> upstream/main
    } finally {
      setLoading(false);
    }
  };

<<<<<<< HEAD
  // View resume
  const handleViewResume = (application) => {
    if (!application.resume_filename) {
      alert("No resume available for this candidate");
      return;
    }

    setSelectedResume({
      application_id: application.application_id,
      filename: application.resume_filename,
      candidate_name: application.candidate_name || application.candidate_email,
      job_title: application.job_title,
    });
    setResumeModalOpen(true);
  };

  // Download resume
  const handleDownloadResume = (application) => {
    if (!application.resume_filename) {
      alert("No resume available for download");
      return;
    }

    const user = JSON.parse(localStorage.getItem("user"));
    const url = `${API_BASE}/download-resume.php?application_id=${application.application_id}&recruiter_id=${user.id}`;
    window.open(url, "_blank");
  };

  // Close resume modal
  const closeResumeModal = () => {
    setResumeModalOpen(false);
    setSelectedResume(null);
  };

  // Update application status
  const handleStatusChange = async (applicationId, newStatus) => {
    const user = JSON.parse(localStorage.getItem("user"));

    setStatusUpdates((prev) => ({
      ...prev,
      [applicationId]: newStatus,
    }));

    try {
      const response = await fetch(`${API_BASE}/update-application-status.php`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          application_id: applicationId,
          status: newStatus,
          recruiter_id: user.id,
        }),
      });

      const data = await response.json();
      if (!data.success) {
        alert("Failed to update status");
        setStatusUpdates((prev) => ({
          ...prev,
          [applicationId]:
            applications.find((app) => app.application_id === applicationId)?.status,
        }));
      }
    } catch (error) {
      console.error("Error updating status:", error);
      alert("Failed to update status");
    }
  };

  // Rank candidates
  const handleRankCandidates = async () => {
    if (!selectedJobForRanking) {
      setRankingError("Please select a job to rank candidates");
      return;
    }

    setRankingLoading(true);
    setRankingError("");

    try {
      const jobApplications = applications.filter(
        (app) => app.job_id?.toString() === selectedJobForRanking.toString()
      );

      if (jobApplications.length === 0) {
        setRankingError("No applications found for this job");
        setRankingLoading(false);
        return;
      }

      const response = await fetch(`${API_BASE}/rank-resumes.php`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_id: selectedJobForRanking,
          applications: jobApplications,
        }),
      });

      const data = await response.json();

      if (data.success) {
        setRankings(data.rankings || []);
      } else {
        setRankingError(data.message || "Failed to rank resumes");
      }
    } catch (err) {
      console.error(err);
      setRankingError("Server error");
    } finally {
      setRankingLoading(false);
    }
  };

  // Get status badge class
  const getStatusClass = (status) => {
    switch (status) {
      case "pending":
        return "status-pending";
      case "reviewed":
        return "status-reviewed";
      case "shortlisted":
        return "status-shortlisted";
      case "rejected":
        return "status-rejected";
      default:
        return "status-pending";
    }
  };

  // Get score badge style
  const getScoreBadge = (score) => {
    if (score >= 0.7) return { text: "Excellent Match", className: "score-excellent" };
    if (score >= 0.5) return { text: "Good Match", className: "score-good" };
    return { text: "Fair Match", className: "score-fair" };
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // Download resume from rankings
  const downloadRankedResume = (filename) => {
    const user = JSON.parse(localStorage.getItem("user"));
    if (!filename) {
      alert("No resume available for download");
      return;
    }
    window.open(
      `${API_BASE}/download-resume.php?filename=${filename}&recruiter_id=${user.id}`,
      "_blank"
    );
  };

  const markNotificationRead = async (notificationId) => {
    const user = JSON.parse(localStorage.getItem("user"));
    if (!user?.id) return;
    try {
      await fetch(`${API_BASE}/mark-notification-read.php`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          notification_id: notificationId,
          user_id: user.id,
        }),
      });
      setNotifications((prev) =>
        prev.map((n) => (n.id === notificationId ? { ...n, is_read: 1 } : n))
      );
    } catch (err) {
      console.error(err);
    }
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const filteredApplications = useMemo(() => {
    if (!selectedJobForRanking) return applications;
    return applications.filter(
      (app) => app.job_id?.toString() === selectedJobForRanking.toString()
    );
  }, [applications, selectedJobForRanking]);

  const groupedApplications = useMemo(() => {
    const groups = {
      pending: [],
      reviewed: [],
      shortlisted: [],
      rejected: [],
    };

    filteredApplications.forEach((app) => {
      const status = app.status || "pending";
      if (!groups[status]) {
        groups[status] = [];
      }
      groups[status].push(app);
    });

    return groups;
  }, [filteredApplications]);

  const filteredByStatus = useMemo(() => {
    if (selectedStatusFilter === "all") return filteredApplications;
    return filteredApplications.filter((app) => (app.status || "pending") === selectedStatusFilter);
  }, [filteredApplications, selectedStatusFilter]);

  return (
    <>
      <header
        className="dashboard-header"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "1rem 2rem",
          background: "white",
          borderBottom: "1px solid #e5e7eb",
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
        }}
      >
        <div style={{ flex: 1 }}>
          <h1 style={{ margin: 0, fontSize: "1.5rem", color: "#1f2937" }}>
            Recruiter Dashboard
          </h1>
          <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.875rem", color: "#6b7280" }}>
            Manage job postings and review candidate applications
          </p>
        </div>
        <div className="dashboard-actions" style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <ProfileIcon />
        </div>
      </header>

      <main className="recruiter-layout">
        <div className="top-row">
          {/* Left: Post Job Form */}
          <section className="card post-job-card">
            <h2>Post New Job</h2>

            <form onSubmit={handlePostJob} className="job-form">
              <label>
                <strong>Job Title</strong>
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                placeholder="e.g., Senior Frontend Developer"
                className="job-input"
              />

              <label>
                <strong>Job Description</strong>
              </label>
              <textarea
                rows="6"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                required
                placeholder="Describe the job responsibilities, requirements, and benefits..."
                className="job-textarea"
              ></textarea>

              <div className="button-group">
                <button type="submit" disabled={loading} className="btn primary">
                  {loading ? "Posting..." : "Post Job"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setTitle("");
                    setDescription("");
                  }}
                  className="btn outline"
                >
                  Clear Form
                </button>
              </div>
            </form>
          </section>

          {/* Center: Applied Candidates */}
          <section className="card applied-card">
            <h2>Applied Candidates</h2>

            <div className="section-block">
              <div className="section-title">Filters</div>
              <div className="filters-bar">
                <div className="filter-item">
                  <label className="toolbar-label">Job</label>
                  {recruiterJobs.length === 0 ? (
                    <div className="no-jobs">No jobs posted yet</div>
                  ) : (
                    <select
                      value={selectedJobForRanking}
                      onChange={(e) => {
                        setSelectedJobForRanking(e.target.value);
                        setRankings([]);
                        setRankingError("");
                      }}
                      className="job-selector"
                    >
                      <option value="">All jobs</option>
                      {recruiterJobs.map((job) => (
                        <option key={job.id} value={job.id}>
                          {job.title} - {new Date(job.created_at).toLocaleDateString()}
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                <div className="filter-item">
                  <label className="toolbar-label">Status</label>
                  <select
                    value={selectedStatusFilter}
                    onChange={(e) => setSelectedStatusFilter(e.target.value)}
                    className="status-filter-select"
                  >
                    <option value="all">All</option>
                    <option value="shortlisted">
                      Shortlisted ({groupedApplications.shortlisted.length})
                    </option>
                    <option value="reviewed">Reviewed ({groupedApplications.reviewed.length})</option>
                    <option value="pending">Pending ({groupedApplications.pending.length})</option>
                    <option value="rejected">Rejected ({groupedApplications.rejected.length})</option>
                  </select>
                </div>
              </div>

              <div className="filters-row">
                <div className="filter-item">
                  {selectedJobForRanking && (
                    <div className="selected-job-info">
                      <h4>
                        {recruiterJobs.find((j) => j.id.toString() === selectedJobForRanking.toString())?.title ||
                          "Selected Job"}
                      </h4>
                      <p>Applications: {filteredApplications.length} candidates</p>
                    </div>
                  )}
                </div>
                <div className="filter-item filter-metric">
                  <div className="toolbar-metric">
                    <span className="metric-value">{filteredApplications.length}</span>
                    <span className="metric-label">Candidates</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="section-block">
              <div className="ranking-accordion">
                <button
                  className="accordion-toggle"
                  onClick={() => setRankingOpen((prev) => !prev)}
                >
                  <span>Ranking</span>
                  <span className="accordion-icon">{rankingOpen ? "−" : "+"}</span>
                </button>

                {rankingOpen && (
                  <div className="ranking-card inline-ranking inline-ranking-top">
                    <h3>Rank Candidates by Match Score</h3>
                    <p className="ranking-subtitle">Select a job and rank candidates who applied for it</p>

                {selectedJobForRanking && (
                  <div className="selected-job-info">
                    <h4>
                      {recruiterJobs.find((j) => j.id.toString() === selectedJobForRanking.toString())?.title ||
                        "Selected Job"}
                    </h4>
                    <p>Applications: {filteredApplications.length} candidates</p>
                  </div>
                )}

                {rankingError && <div className="ranking-error">{rankingError}</div>}

                <button
                  onClick={handleRankCandidates}
                  disabled={rankingLoading || !selectedJobForRanking}
                  className="rank-button"
                >
                  {rankingLoading ? (
                    <>
                      <span className="spinner"></span>
                      Analyzing Resumes...
                    </>
                  ) : (
                    <>
                      <span className="rank-icon">Rank</span>
                      Rank Candidates
                    </>
                  )}
                </button>

                    {rankings.length > 0 && (
                  <div className="rankings-results">
                    <h3>Candidate Rankings</h3>

                    <div className="rankings-list">
                      {rankings.map((candidate, index) => {
                        const badge = getScoreBadge(candidate.score);
                        return (
                          <div key={index} className={`ranking-item ${index === 0 ? "top-ranking" : ""}`}>
                            <div className="ranking-header">
                              <div className="rank-number">{index + 1}</div>
                              <div className="candidate-info">
                                <h4>
                                  {candidate.candidate_name || candidate.candidate_email || `Candidate ${candidate.candidate_id}`}
                                </h4>
                                <span className={`score-badge ${badge.className}`}>{badge.text}</span>
                              </div>
                              <div className="score-display">
                                <div className="score-value">{(candidate.score * 100).toFixed(1)}%</div>
                                <div className="score-label">Match Score</div>
                              </div>
                            </div>

                            <div className="progress-bar">
                              <div className="progress-fill" style={{ width: `${candidate.score * 100}%` }}></div>
                            </div>

                            <div className="candidate-details">
                              <div className="detail-group">
                                <strong>Resume:</strong>
                                {candidate.resume_filename ? (
                                  <button
                                    onClick={() => downloadRankedResume(candidate.resume_filename)}
                                    className="resume-link"
                                  >
                                    {candidate.resume_filename}
                                  </button>
                                ) : (
                                  <span>No resume</span>
                                )}
                              </div>
                              <div className="detail-group">
                                <strong>Applied:</strong>
                                <span>{formatDate(candidate.applied_at)}</span>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    <div className="summary-stats">
                      <div className="stat-card excellent">
                        <div className="stat-title">Excellent Matches</div>
                        <div className="stat-value">{rankings.filter((r) => r.score >= 0.7).length}</div>
                      </div>
                      <div className="stat-card good">
                        <div className="stat-title">Good Matches</div>
                        <div className="stat-value">
                          {rankings.filter((r) => r.score >= 0.5 && r.score < 0.7).length}
                        </div>
                      </div>
                      <div className="stat-card average">
                        <div className="stat-title">Average Score</div>
                        <div className="stat-value">
                          {rankings.length > 0
                            ? ((rankings.reduce((sum, r) => sum + r.score, 0) / rankings.length) * 100).toFixed(1) +
                              "%"
                            : "0%"}
                        </div>
                      </div>
                    </div>
                  </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="section-block">
              <div className="section-title">Candidates</div>

              {applicationsLoading && (
                <div className="empty-state">
                  <p>Loading applications...</p>
                </div>
              )}

              {!applicationsLoading && applicationsError && (
                <div className="applications-error">{applicationsError}</div>
              )}

              {!applicationsLoading && !applicationsError && filteredApplications.length === 0 ? (
                <div className="empty-state">
                  <p>No applications found for the selected job.</p>
                  <p>Applications will appear here when candidates apply.</p>
                </div>
              ) : (
                <div className="applications-list">
                  {filteredByStatus.length ? (
                    filteredByStatus.map((app) => (
                      <div key={app.application_id} className="application-card">
                        <div className="application-header">
                          <div>
                            <div className="candidate-name">
                              {app.candidate_name || app.candidate_email || "Unknown Candidate"}
                            </div>
                            <span className={`application-status ${getStatusClass(app.status)}`}>
                              {app.status?.charAt(0).toUpperCase() + app.status?.slice(1) || "Pending"}
                            </span>
                          </div>
                          <div className="application-date">{formatDate(app.applied_at)}</div>
                        </div>

                        <div className="application-details">
                          <div>
                            <strong>Email:</strong> {app.candidate_email || "N/A"}
                          </div>
                          <div>
                            <strong>Job:</strong> {app.job_title || "N/A"}
                          </div>
                        </div>

                        <div className="resume-section">
                          <strong>Resume:</strong>
                          {app.resume_filename ? (
                            <div className="resume-actions">
                              <button onClick={() => handleViewResume(app)} className="btn-resume btn-view">
                                View Resume
                              </button>
                              <button onClick={() => handleDownloadResume(app)} className="btn-resume btn-download">
                                Download
                              </button>
                            </div>
                          ) : (
                            <span className="no-resume"> No resume uploaded</span>
                          )}
                        </div>

                        <div className="portfolio-section">
                          <strong>Portfolio Links:</strong>
                          {app.portfolio_links && app.portfolio_links.length > 0 ? (
                            <div className="portfolio-links">
                              {app.portfolio_links.map((link, index) => (
                                <a
                                  key={`${app.application_id}-link-${index}`}
                                  href={link.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="portfolio-link"
                                >
                                  {link.label}
                                </a>
                              ))}
                            </div>
                          ) : (
                            <span className="no-resume"> No links found</span>
                          )}
                        </div>

                        <div className="status-row">
                          <label>
                            <strong>Update Status:</strong>
                          </label>
                          <select
                            value={statusUpdates[app.application_id] || app.status || "pending"}
                            onChange={(e) => handleStatusChange(app.application_id, e.target.value)}
                            className="status-selector"
                          >
                            <option value="pending">Pending</option>
                            <option value="reviewed">Reviewed</option>
                            <option value="shortlisted">Shortlisted</option>
                            <option value="rejected">Rejected</option>
                          </select>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="status-empty">No candidates in this filter.</div>
                  )}
                </div>
              )}
            </div>
          </section>

          {/* Right: Notifications */}
          <section className="card notifications-card">
            <h2>Notifications</h2>
            <div className="notifications-panel">
              <div className="notifications-header">
                <h3>Updates</h3>
                <span className={`notifications-badge ${unreadCount > 0 ? "unread" : ""}`}>
                  {unreadCount} unread
                </span>
              </div>

              <div className="notifications-list">
                {notificationsLoading && (
                  <div className="notifications-empty">Loading notifications...</div>
                )}
                {!notificationsLoading && notificationsError && (
                  <div className="notifications-error">{notificationsError}</div>
                )}
                {!notificationsLoading && !notificationsError && notifications.length === 0 && (
                  <div className="notifications-empty">No notifications yet.</div>
                )}
                {!notificationsLoading &&
                  !notificationsError &&
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      className={`notification-item ${n.is_read ? "" : "unread"}`}
                    >
                      <div className="notification-message">
                        {n.message || `New application status: ${n.status}`}
                      </div>
                      <div className="notification-meta">
                        {formatDate(n.created_at)}
                      </div>
                      {!n.is_read && (
                        <button
                          className="notification-read"
                          onClick={() => markNotificationRead(n.id)}
                        >
                          Mark as read
                        </button>
                      )}
                    </div>
                  ))}
              </div>
            </div>
          </section>
        </div>
      </main>

      {resumeModalOpen && selectedResume && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 style={{ margin: 0 }}>
                Resume: {selectedResume.candidate_name} - {selectedResume.job_title}
              </h3>
              <button onClick={closeResumeModal} className="modal-close">
                x
              </button>
            </div>
            <div className="modal-body">
              {selectedResume.filename && selectedResume.filename.endsWith(".pdf") ? (
                <iframe
                  src={`${API_BASE}/download-resume.php?application_id=${selectedResume.application_id}&recruiter_id=${
                    JSON.parse(localStorage.getItem("user"))?.id
                  }`}
                  title="Resume Preview"
                  className="resume-frame"
                />
              ) : (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    height: "100%",
                    textAlign: "center",
                  }}
                >
                  <h3>Document Preview</h3>
                  <p>This document type cannot be previewed in browser.</p>
                  <p>Please download to view.</p>
                  <button
                    onClick={() =>
                      window.open(
                        `${API_BASE}/download-resume.php?application_id=${selectedResume.application_id}&recruiter_id=${
                          JSON.parse(localStorage.getItem("user"))?.id
                        }`,
                        "_blank"
                      )
                    }
                    className="btn primary"
                    style={{ marginTop: "1rem" }}
                  >
                    Download Resume
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <footer className="dashboard-footer">
        <p>&copy; 2025 Job Nexus - Recruiter Dashboard</p>
        <p style={{ fontSize: "0.9rem", marginTop: "0.5rem" }}>
          {applications.length} total applications • Last updated: {new Date().toLocaleDateString()}
        </p>
      </footer>
=======
  return (
    <>
      <header>
        <h1>Recruiter Dashboard</h1>
      </header>

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
          <h2>Post Job</h2>

          <form onSubmit={handlePostJob}>
            <label>Job Title</label><br />
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            /><br /><br />

            <label>Job Description</label><br />
            <textarea
              rows="4"
              cols="40"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
            ></textarea><br /><br />

            <button className="btn" type="submit" disabled={loading}>
              {loading ? "Posting..." : "Post Job"}
            </button>
          </form>
        </section>

        <section className="card">
          <h2>Resume Analysis</h2>
          <ul>
            <li>Bulk upload candidate resumes</li>
            <li>Rank candidates by match score</li>
            <li>Shortlist and contact matched talent</li>
            <li>Connect with college admins for campus hiring</li>
          </ul>
        </section>
      </main>

      <footer>&copy; 2025 Job Nexus</footer>
>>>>>>> upstream/main
    </>
  );
}
