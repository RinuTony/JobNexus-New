<<<<<<< HEAD
import React, { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

const API_BASE = "http://localhost:8000";

export default function InterviewPrep() {
  const location = useLocation();
  const { jobId, jobTitle, resumeSelection } = location.state || {};
  const user = JSON.parse(localStorage.getItem("user"));

  const [jobDetails, setJobDetails] = useState(jobTitle ? { title: jobTitle } : null);
  const [sessionId, setSessionId] = useState(null);
  const [totalQuestions, setTotalQuestions] = useState(10);
  const [interviewQuestions, setInterviewQuestions] = useState([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [feedback, setFeedback] = useState({});
  const [feedbackAudio, setFeedbackAudio] = useState({});
  const [loading, setLoading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [interviewStarted, setInterviewStarted] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [finalScore, setFinalScore] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsError, setSessionsError] = useState("");
  const [reviewSession, setReviewSession] = useState(null);
  const [reviewLoading, setReviewLoading] = useState(false);

  useEffect(() => {
    if (jobId && !jobDetails) {
      fetchJobDetails(jobId);
    }
  }, [jobId, jobDetails]);

  const fetchJobDetails = async (jobIdValue) => {
    try {
      const response = await fetch(`${API_BASE}/api/job/${jobIdValue}`);
      const data = await response.json();
      if (data.success) {
        setJobDetails(data.job);
      }
    } catch (error) {
      console.error("Error fetching job details:", error);
    }
  };

  const startOrResumeInterview = useCallback(async () => {
    setLoading(true);
    setErrorMessage("");
    setInterviewQuestions([]);
    setCurrentQuestionIndex(0);
    setAnswers({});
    setFeedback({});
    setFeedbackAudio({});
    setFinalScore(null);

    try {
      const resumeResponse = await fetch(`${API_BASE}/api/interview/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate_id: String(user.id),
          job_id: String(jobId),
        }),
      });

      if (resumeResponse.ok) {
        const resumeData = await resumeResponse.json();
        if (resumeData.total_questions) {
          setTotalQuestions(resumeData.total_questions);
        }
        if (resumeData.success && resumeData.next_question) {
          setSessionId(resumeData.session_id);
          appendQuestion(resumeData.next_question);
          setInterviewStarted(true);
          return;
        }
        if (resumeData.done) {
          setFinalScore(resumeData.final_score ?? 0);
          setInterviewStarted(false);
          return;
        }
      }

      const startResponse = await fetch(`${API_BASE}/api/interview/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate_id: String(user.id),
          job_id: String(jobId),
          question_count: 10,
          include_audio: true,
          resume_type: resumeSelection?.source === "builder" ? "builder" : resumeSelection?.source === "uploaded" ? "uploaded" : "latest",
          resume_id: resumeSelection?.source === "builder" ? String(resumeSelection.id) : null,
          resume_filename: resumeSelection?.source === "uploaded" ? resumeSelection.filename : null,
        }),
      });

      const startData = await startResponse.json();
      if (!startResponse.ok) {
        throw new Error(startData.detail || "Failed to start interview");
      }

      setSessionId(startData.session_id);
      setTotalQuestions(startData.total_questions || 10);
      appendQuestion(startData.next_question);
      setInterviewStarted(true);
    } catch (err) {
      console.error(err);
      setErrorMessage(
        "Unable to start interview. Make sure the FastAPI and interview services are running."
      );
    } finally {
      setLoading(false);
    }
  }, [jobId, resumeSelection, user?.id]);

  useEffect(() => {
    // Keep landing state so user can choose start new or review.
  }, [jobId, user?.id]);

  const fetchSessions = useCallback(async () => {
    if (!user?.id) return;
    setSessionsLoading(true);
    setSessionsError("");
    try {
      const params = new URLSearchParams({
        candidate_id: String(user.id)
      });
      if (jobId) params.set("job_id", String(jobId));
      const response = await fetch(`${API_BASE}/api/interview/sessions?${params.toString()}`);
      const data = await response.json();
      if (data.success) {
        setSessions(data.sessions || []);
      } else {
        setSessionsError(data.detail || "Failed to load interview sessions.");
      }
    } catch (err) {
      console.error(err);
      setSessionsError("Failed to load interview sessions.");
    } finally {
      setSessionsLoading(false);
    }
  }, [jobId, user?.id]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const startNewInterview = async () => {
    if (!jobId || !user?.id) return;
    setLoading(true);
    setErrorMessage("");
    setInterviewQuestions([]);
    setCurrentQuestionIndex(0);
    setAnswers({});
    setFeedback({});
    setFeedbackAudio({});
    setFinalScore(null);
    setReviewSession(null);

    try {
      const startResponse = await fetch(`${API_BASE}/api/interview/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate_id: String(user.id),
          job_id: String(jobId),
          question_count: 10,
          include_audio: true,
          resume_type: resumeSelection?.source === "builder" ? "builder" : resumeSelection?.source === "uploaded" ? "uploaded" : "latest",
          resume_id: resumeSelection?.source === "builder" ? String(resumeSelection.id) : null,
          resume_filename: resumeSelection?.source === "uploaded" ? resumeSelection.filename : null,
        }),
      });

      const startData = await startResponse.json();
      if (!startResponse.ok) {
        throw new Error(startData.detail || "Failed to start interview");
      }

      setSessionId(startData.session_id);
      setTotalQuestions(startData.total_questions || 10);
      appendQuestion(startData.next_question);
      setInterviewStarted(true);
      fetchSessions();
    } catch (err) {
      console.error(err);
      setErrorMessage("Unable to start interview. Make sure the FastAPI and interview services are running.");
=======
import React, { useState } from "react";

export default function InterviewPrep() {
  const [resume, setResume] = useState(null);
  const [jd, setJd] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [feedback, setFeedback] = useState({});
  const [loading, setLoading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [interviewStarted, setInterviewStarted] = useState(false);

  const startInterview = async () => {
    if (!resume || !jd) {
      alert("Please upload both Resume and Job Description PDFs");
      return;
    }

    const formData = new FormData();
    formData.append("resume", resume);
    formData.append("job_description", jd);

    setLoading(true);

    try {
      const response = await fetch("http://localhost:5000/start-interview", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();
      console.log("Backend response:", data);

      if (!data.questions || data.questions.length === 0) {
        alert("Failed to generate questions. Please try again.");
        return;
      }

      if (data.questions.length === 1 && data.questions[0].toLowerCase().includes("error")) {
        alert(data.questions[0]);
        return;
      }

      setQuestions(data.questions);
      setInterviewStarted(true);
      setCurrentQuestionIndex(0);
      setAnswers({});
      setFeedback({});
      
    } catch (err) {
      console.error(err);
      alert("Unable to connect to backend. Make sure the Flask server is running on port 5000.");
>>>>>>> upstream/main
    } finally {
      setLoading(false);
    }
  };

<<<<<<< HEAD
  const reviewInterviewSession = async (sessionId) => {
    setReviewLoading(true);
    setReviewSession(null);
    try {
      const response = await fetch(`${API_BASE}/api/interview/session/${sessionId}`);
      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.detail || "Failed to load interview session");
      }
      setReviewSession(data);
    } catch (err) {
      console.error(err);
      setErrorMessage("Failed to load interview session.");
    } finally {
      setReviewLoading(false);
    }
  };

  const appendQuestion = (question) => {
    setInterviewQuestions((prev) => {
      const next = [...prev, question];
      setCurrentQuestionIndex(next.length - 1);
      return next;
    });
  };

  const currentQuestion = interviewQuestions[currentQuestionIndex];

=======
>>>>>>> upstream/main
  const handleAnswerChange = (e) => {
    const newAnswers = { ...answers };
    newAnswers[currentQuestionIndex] = e.target.value;
    setAnswers(newAnswers);
  };

<<<<<<< HEAD
  const toAudioSrc = (base64, mime) => {
    if (!base64 || !mime) return "";
    return `data:${mime};base64,${base64}`;
  };


  const evaluateAnswer = async () => {
    if (!currentQuestion) return;
    const currentAnswer = answers[currentQuestionIndex] || "";
    if (!currentAnswer.trim()) {
      alert("Please type your answer before evaluating.");
=======
  const evaluateAnswer = async () => {
    const currentQuestion = questions[currentQuestionIndex];
    const currentAnswer = answers[currentQuestionIndex];

    if (!currentAnswer || currentAnswer.trim() === "") {
      alert("Please provide an answer before evaluating.");
>>>>>>> upstream/main
      return;
    }

    setEvaluating(true);
<<<<<<< HEAD
    setErrorMessage("");

    try {
      const response = await fetch(`${API_BASE}/api/interview/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          question_id: currentQuestion.id,
          answer_text: currentAnswer.trim(),
          answer_audio_base64: null,
          audio_format: null,
          sample_rate_hz: null,
          include_audio: true,
        }),
      });

      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.detail || "Failed to evaluate answer");
      }

      setFeedback((prev) => ({ ...prev, [currentQuestionIndex]: data.feedback }));
      setFeedbackAudio((prev) => ({
        ...prev,
        [currentQuestionIndex]: {
          base64: data.feedback_audio_base64,
          mime: data.feedback_audio_mime,
        },
      }));

      if (data.answer_text) {
        setAnswers((prev) => ({ ...prev, [currentQuestionIndex]: data.answer_text }));
      }
    } catch (err) {
      console.error(err);
      setErrorMessage("Failed to evaluate answer. Please try again.");
=======

    try {
      const response = await fetch("http://localhost:5000/evaluate-answer", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: currentQuestion,
          answer: currentAnswer,
        }),
      });

      if (!response.ok) {
        throw new Error(`Evaluation error: ${response.status}`);
      }

      const data = await response.json();
      console.log("Evaluation response:", data);

      const newFeedback = { ...feedback };
      newFeedback[currentQuestionIndex] = data.feedback;
      setFeedback(newFeedback);

    } catch (err) {
      console.error(err);
      alert("Failed to evaluate answer. Please try again.");
>>>>>>> upstream/main
    } finally {
      setEvaluating(false);
    }
  };

<<<<<<< HEAD
  const goToNextQuestion = async () => {
    if (currentQuestionIndex < interviewQuestions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/interview/next`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.detail || "Failed to load next question");
      }
      if (data.done) {
        setFinalScore(data.final_score ?? 0);
        setInterviewStarted(false);
        return;
      }
      appendQuestion(data.next_question);
    } catch (err) {
      console.error(err);
      setErrorMessage("Unable to load the next question.");
=======
  const goToNextQuestion = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
>>>>>>> upstream/main
    }
  };

  const goToPreviousQuestion = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
    }
  };

<<<<<<< HEAD
  const stopInterview = async () => {
    if (!sessionId) return;
    try {
      await fetch(`${API_BASE}/api/interview/stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      setInterviewStarted(false);
    } catch (err) {
      console.error(err);
      setErrorMessage("Failed to stop interview.");
    }
=======
  const resetInterview = () => {
    setQuestions([]);
    setAnswers({});
    setFeedback({});
    setInterviewStarted(false);
    setCurrentQuestionIndex(0);
    setResume(null);
    setJd(null);
>>>>>>> upstream/main
  };

  const calculateOverallScore = () => {
    const scores = Object.values(feedback)
<<<<<<< HEAD
      .filter((f) => f && typeof f.score === "number")
      .map((f) => f.score);
    if (scores.length === 0) return 0;
=======
      .filter(f => f && typeof f.score === 'number')
      .map(f => f.score);
    
    if (scores.length === 0) return 0;
    
>>>>>>> upstream/main
    return (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1);
  };

  return (
<<<<<<< HEAD
    <div className="interview-prep-container" style={{ padding: "20px", maxWidth: "900px", margin: "0 auto" }}>
      <h2>AI Interview Preparation</h2>

      {!jobId && (
        <div style={{ marginBottom: "20px", padding: "12px", backgroundColor: "#fef2f2", borderRadius: "6px" }}>
          <p style={{ margin: 0, color: "#b91c1c", fontSize: "14px" }}>
            Missing job information. Please start interview prep from the Jobs page.
          </p>
        </div>
      )}

      {jobDetails && (
        <div
          style={{
            backgroundColor: "#f0f9ff",
            padding: "15px",
            borderRadius: "8px",
            marginBottom: "20px",
            borderLeft: "4px solid #3b82f6",
          }}
        >
          <h3 style={{ margin: 0, color: "#1e40af" }}>Preparing for: {jobDetails.title}</h3>
          {jobDetails.description && (
            <p style={{ marginTop: "8px", color: "#374151", fontSize: "0.95rem" }}>
              {jobDetails.description.length > 200
                ? `${jobDetails.description.substring(0, 200)}...`
                : jobDetails.description}
            </p>
          )}
        </div>
      )}

      {errorMessage && (
        <div style={{ marginBottom: "20px", padding: "12px", backgroundColor: "#fef2f2", borderRadius: "6px" }}>
          <p style={{ margin: 0, color: "#b91c1c", fontSize: "14px" }}>{errorMessage}</p>
        </div>
      )}

      {loading && <p>Loading interview...</p>}

      {!loading && !interviewStarted && (
        <div style={{ marginBottom: "20px", padding: "16px", border: "1px solid #e5e7eb", borderRadius: "8px" }}>
          <p style={{ margin: "0 0 12px 0" }}>
            Ready to start your interview? You can resume the latest session or start a new one.
          </p>
          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            <button
              onClick={startOrResumeInterview}
              style={{
                padding: "10px 16px",
                backgroundColor: "#4f46e5",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              Resume Latest
            </button>
            <button
              onClick={startNewInterview}
              style={{
                padding: "10px 16px",
                backgroundColor: "#059669",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              Start New Interview
            </button>
          </div>
        </div>
      )}

      {!loading && !interviewStarted && (
        <div style={{ marginBottom: "20px" }}>
          <h3 style={{ marginBottom: "10px" }}>Previous Interviews</h3>
          {sessionsLoading && <p>Loading interview history...</p>}
          {!sessionsLoading && sessionsError && (
            <div style={{ marginBottom: "12px", color: "#b91c1c" }}>{sessionsError}</div>
          )}
          {!sessionsLoading && !sessionsError && sessions.length === 0 && (
            <div style={{ color: "#6b7280" }}>No previous interviews yet.</div>
          )}
          {!sessionsLoading && !sessionsError && sessions.length > 0 && (
            <div style={{ display: "grid", gap: "10px" }}>
              {sessions.map((session) => (
                <div key={session.id} style={{ border: "1px solid #e5e7eb", borderRadius: "8px", padding: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px" }}>
                    <div>
                      <div style={{ fontWeight: "600", color: "#111827" }}>
                        Session #{session.id} {session.status === "completed" ? "(Completed)" : "(In Progress)"}
                      </div>
                      <div style={{ fontSize: "12px", color: "#6b7280" }}>
                        Questions: {session.asked_count}/{session.total_questions} • Final Score: {session.final_score ?? 0}/10
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: "8px" }}>
                      <button
                        onClick={() => reviewInterviewSession(session.id)}
                        style={{
                          padding: "6px 10px",
                          backgroundColor: "#e5e7eb",
                          color: "#111827",
                          border: "none",
                          borderRadius: "6px",
                          cursor: "pointer",
                        }}
                      >
                        Review
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!loading && interviewStarted && currentQuestion && (
        <div className="interview-section">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
            <h3>Interview in Progress</h3>
            <button
              onClick={stopInterview}
=======
    <div className="interview-prep-container" style={{ padding: "20px", maxWidth: "800px", margin: "0 auto" }}>
      <h2>AI Interview Preparation</h2>
      
      {!interviewStarted ? (
        <div className="upload-section" style={{ marginBottom: "30px", padding: "20px", border: "1px solid #ddd", borderRadius: "8px" }}>
          <h3>Step 1: Upload Documents</h3>
          
          <div style={{ marginBottom: "15px" }}>
            <label style={{ display: "block", marginBottom: "5px", fontWeight: "bold" }}>
              Upload Resume (PDF):
            </label>
            <input 
              type="file" 
              accept=".pdf" 
              onChange={(e) => setResume(e.target.files[0])}
              style={{ padding: "8px" }}
            />
            {resume && <p style={{ color: "green", marginTop: "5px" }}>✓ {resume.name}</p>}
          </div>

          <div style={{ marginBottom: "20px" }}>
            <label style={{ display: "block", marginBottom: "5px", fontWeight: "bold" }}>
              Upload Job Description (PDF):
            </label>
            <input 
              type="file" 
              accept=".pdf" 
              onChange={(e) => setJd(e.target.files[0])}
              style={{ padding: "8px" }}
            />
            {jd && <p style={{ color: "green", marginTop: "5px" }}>✓ {jd.name}</p>}
          </div>

          <button 
            onClick={startInterview} 
            disabled={loading || !resume || !jd}
            style={{
              padding: "12px 24px",
              backgroundColor: loading ? "#ccc" : "#4f46e5",
              color: "white",
              border: "none",
              borderRadius: "6px",
              cursor: loading ? "not-allowed" : "pointer",
              fontSize: "16px",
            }}
          >
            {loading ? "Generating Questions..." : "Start Interview"}
          </button>
        </div>
      ) : (
        <div className="interview-section">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
            <h3>Interview in Progress</h3>
            <button 
              onClick={resetInterview}
>>>>>>> upstream/main
              style={{
                padding: "8px 16px",
                backgroundColor: "#dc2626",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
<<<<<<< HEAD
              Stop Interview
            </button>
          </div>

          <div style={{ marginBottom: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "5px" }}>
              <span>
                Question {currentQuestionIndex + 1} of {totalQuestions}
              </span>
              <span>Overall Score: {calculateOverallScore()}/10</span>
            </div>
            <div style={{ height: "8px", backgroundColor: "#e5e7eb", borderRadius: "4px" }}>
              <div
                style={{
                  width: `${Math.min(((currentQuestionIndex + 1) / totalQuestions) * 100, 100)}%`,
                  height: "100%",
                  backgroundColor: "#4f46e5",
                  borderRadius: "4px",
                  transition: "width 0.3s",
=======
              Restart Interview
            </button>
          </div>

          {/* Progress indicator */}
          <div style={{ marginBottom: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "5px" }}>
              <span>Question {currentQuestionIndex + 1} of {questions.length}</span>
              <span>Overall Score: {calculateOverallScore()}/10</span>
            </div>
            <div style={{ height: "8px", backgroundColor: "#e5e7eb", borderRadius: "4px" }}>
              <div 
                style={{ 
                  width: `${((currentQuestionIndex + 1) / questions.length) * 100}%`, 
                  height: "100%", 
                  backgroundColor: "#4f46e5",
                  borderRadius: "4px",
                  transition: "width 0.3s"
>>>>>>> upstream/main
                }}
              ></div>
            </div>
          </div>

<<<<<<< HEAD
=======
          {/* Current Question */}
>>>>>>> upstream/main
          <div className="question-card" style={{ marginBottom: "30px", padding: "20px", border: "1px solid #ddd", borderRadius: "8px" }}>
            <h4 style={{ marginBottom: "15px", color: "#374151" }}>
              Question {currentQuestionIndex + 1}:
            </h4>
<<<<<<< HEAD
            <p style={{ fontSize: "18px", marginBottom: "12px" }}>{currentQuestion.question_text}</p>

            {currentQuestion.question_audio_base64 && (
              <audio
                controls
                src={toAudioSrc(currentQuestion.question_audio_base64, currentQuestion.question_audio_mime)}
                style={{ width: "100%", marginBottom: "16px" }}
              />
            )}

          <div style={{ marginBottom: "20px" }}>
            <label style={{ display: "block", marginBottom: "8px", fontWeight: "bold" }}>Your Answer:</label>
            <textarea
              value={answers[currentQuestionIndex] || ""}
              onChange={handleAnswerChange}
              placeholder="Type your answer here..."
              rows="6"
              style={{
                width: "100%",
                padding: "12px",
                border: "1px solid #d1d5db",
                borderRadius: "6px",
                fontSize: "16px",
                resize: "vertical",
              }}
            />
          </div>

            <div style={{ marginBottom: "16px" }} />

            <div style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
              <button
                onClick={evaluateAnswer}
                disabled={evaluating}
=======
            <p style={{ fontSize: "18px", marginBottom: "20px" }}>{questions[currentQuestionIndex]}</p>

            {/* Answer Input */}
            <div style={{ marginBottom: "20px" }}>
              <label style={{ display: "block", marginBottom: "8px", fontWeight: "bold" }}>
                Your Answer:
              </label>
              <textarea
                value={answers[currentQuestionIndex] || ""}
                onChange={handleAnswerChange}
                placeholder="Type your answer here..."
                rows="6"
                style={{
                  width: "100%",
                  padding: "12px",
                  border: "1px solid #d1d5db",
                  borderRadius: "6px",
                  fontSize: "16px",
                  resize: "vertical",
                }}
              />
            </div>

            {/* Action Buttons */}
            <div style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
              <button
                onClick={evaluateAnswer}
                disabled={evaluating || !answers[currentQuestionIndex]}
>>>>>>> upstream/main
                style={{
                  padding: "10px 20px",
                  backgroundColor: evaluating ? "#ccc" : "#059669",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
<<<<<<< HEAD
                  cursor: evaluating ? "not-allowed" : "pointer",
=======
                  cursor: evaluating || !answers[currentQuestionIndex] ? "not-allowed" : "pointer",
>>>>>>> upstream/main
                  flex: 1,
                }}
              >
                {evaluating ? "Evaluating..." : "Get AI Feedback"}
              </button>
            </div>

<<<<<<< HEAD
=======
            {/* Navigation Buttons */}
>>>>>>> upstream/main
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <button
                onClick={goToPreviousQuestion}
                disabled={currentQuestionIndex === 0}
                style={{
                  padding: "8px 16px",
                  backgroundColor: currentQuestionIndex === 0 ? "#f3f4f6" : "#4f46e5",
                  color: currentQuestionIndex === 0 ? "#9ca3af" : "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: currentQuestionIndex === 0 ? "not-allowed" : "pointer",
                }}
              >
                Previous Question
              </button>
<<<<<<< HEAD

              <button
                onClick={goToNextQuestion}
                style={{
                  padding: "8px 16px",
                  backgroundColor: "#4f46e5",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                }}
              >
                Next Question
              </button>
            </div>
          </div>

          {feedback[currentQuestionIndex] && (
            <div
              className="feedback-card"
              style={{
                marginTop: "30px",
                padding: "20px",
                border: "1px solid #10b981",
                borderRadius: "8px",
                backgroundColor: "#f0fdf4",
              }}
            >
              <h4 style={{ marginBottom: "15px", color: "#065f46" }}>
                AI Feedback{" "}
                {feedback[currentQuestionIndex].score !== undefined
                  ? `(Score: ${feedback[currentQuestionIndex].score}/10)`
                  : ""}
              </h4>

              {feedbackAudio[currentQuestionIndex]?.base64 && (
                <audio
                  controls
                  src={toAudioSrc(
                    feedbackAudio[currentQuestionIndex].base64,
                    feedbackAudio[currentQuestionIndex].mime
                  )}
                  style={{ width: "100%", marginBottom: "16px" }}
                />
              )}

=======
              
              {currentQuestionIndex < questions.length - 1 ? (
                <button
                  onClick={goToNextQuestion}
                  style={{
                    padding: "8px 16px",
                    backgroundColor: "#4f46e5",
                    color: "white",
                    border: "none",
                    borderRadius: "4px",
                    cursor: "pointer",
                  }}
                >
                  Next Question
                </button>
              ) : (
                <button
                  style={{
                    padding: "8px 16px",
                    backgroundColor: "#059669",
                    color: "white",
                    border: "none",
                    borderRadius: "4px",
                    cursor: "pointer",
                  }}
                >
                  Complete Interview
                </button>
              )}
            </div>
          </div>

          {/* Feedback Section */}
          {feedback[currentQuestionIndex] && (
            <div className="feedback-card" style={{ 
              marginTop: "30px", 
              padding: "20px", 
              border: "1px solid #10b981",
              borderRadius: "8px",
              backgroundColor: "#f0fdf4"
            }}>
              <h4 style={{ marginBottom: "15px", color: "#065f46" }}>
                AI Feedback {feedback[currentQuestionIndex].score !== undefined ? `(Score: ${feedback[currentQuestionIndex].score}/10)` : ''}
              </h4>
              
>>>>>>> upstream/main
              {feedback[currentQuestionIndex].error ? (
                <p style={{ color: "#dc2626" }}>Error: {feedback[currentQuestionIndex].error}</p>
              ) : (
                <>
                  {feedback[currentQuestionIndex].strength && (
                    <div style={{ marginBottom: "15px" }}>
                      <h5 style={{ color: "#065f46", marginBottom: "8px" }}>Strengths:</h5>
                      <ul style={{ marginLeft: "20px" }}>
                        {feedback[currentQuestionIndex].strength.map((item, index) => (
<<<<<<< HEAD
                          <li key={index} style={{ marginBottom: "5px" }}>
                            {item}
                          </li>
=======
                          <li key={index} style={{ marginBottom: "5px" }}>{item}</li>
>>>>>>> upstream/main
                        ))}
                      </ul>
                    </div>
                  )}
<<<<<<< HEAD

=======
                  
>>>>>>> upstream/main
                  {feedback[currentQuestionIndex].improvement && (
                    <div>
                      <h5 style={{ color: "#b91c1c", marginBottom: "8px" }}>Areas for Improvement:</h5>
                      <ul style={{ marginLeft: "20px" }}>
                        {feedback[currentQuestionIndex].improvement.map((item, index) => (
<<<<<<< HEAD
                          <li key={index} style={{ marginBottom: "5px" }}>
                            {item}
                          </li>
=======
                          <li key={index} style={{ marginBottom: "5px" }}>{item}</li>
>>>>>>> upstream/main
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

<<<<<<< HEAD
          <div style={{ marginTop: "40px" }}>
            <h4>Questions So Far</h4>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "10px" }}>
              {interviewQuestions.map((question, index) => (
                <div
                  key={question.id}
=======
          {/* All Questions Overview */}
          <div style={{ marginTop: "40px" }}>
            <h4>All Questions</h4>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "10px" }}>
              {questions.map((question, index) => (
                <div 
                  key={index}
>>>>>>> upstream/main
                  onClick={() => setCurrentQuestionIndex(index)}
                  style={{
                    padding: "12px",
                    border: "2px solid",
<<<<<<< HEAD
                    borderColor:
                      currentQuestionIndex === index ? "#4f46e5" : feedback[index] ? "#10b981" : "#d1d5db",
                    borderRadius: "6px",
                    backgroundColor:
                      currentQuestionIndex === index ? "#eef2ff" : feedback[index] ? "#f0fdf4" : "white",
=======
                    borderColor: currentQuestionIndex === index ? "#4f46e5" : 
                                 feedback[index] ? "#10b981" : "#d1d5db",
                    borderRadius: "6px",
                    backgroundColor: currentQuestionIndex === index ? "#eef2ff" : 
                                   feedback[index] ? "#f0fdf4" : "white",
>>>>>>> upstream/main
                    cursor: "pointer",
                    transition: "all 0.2s",
                  }}
                >
<<<<<<< HEAD
                  <div style={{ fontSize: "14px", fontWeight: "bold", marginBottom: "5px" }}>Q{index + 1}</div>
                  <div style={{ fontSize: "12px", color: "#6b7280", height: "40px", overflow: "hidden" }}>
                    {question.question_text.substring(0, 60)}...
=======
                  <div style={{ fontSize: "14px", fontWeight: "bold", marginBottom: "5px" }}>
                    Q{index + 1}
                  </div>
                  <div style={{ fontSize: "12px", color: "#6b7280", height: "40px", overflow: "hidden" }}>
                    {question.substring(0, 60)}...
>>>>>>> upstream/main
                  </div>
                  <div style={{ fontSize: "12px", marginTop: "5px" }}>
                    {feedback[index] ? (
                      <span style={{ color: "#059669" }}>✓ Score: {feedback[index].score}/10</span>
                    ) : answers[index] ? (
                      <span style={{ color: "#f59e0b" }}>✎ Answered</span>
                    ) : (
                      <span style={{ color: "#9ca3af" }}>Not answered</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
<<<<<<< HEAD

      {!loading && !interviewStarted && finalScore !== null && (
        <div style={{ marginTop: "20px", padding: "16px", border: "1px solid #e5e7eb", borderRadius: "8px", backgroundColor: "#f0fdf4" }}>
          <h3 style={{ marginTop: 0, color: "#065f46" }}>Interview Complete</h3>
          <p style={{ margin: 0, color: "#065f46" }}>Final Score: {finalScore}/10</p>
        </div>
      )}

      {!loading && !interviewStarted && reviewLoading && (
        <div style={{ marginTop: "20px" }}>
          <p>Loading interview session...</p>
        </div>
      )}

      {!loading && !interviewStarted && reviewSession && (
        <div style={{ marginTop: "20px", padding: "16px", border: "1px solid #e5e7eb", borderRadius: "8px", backgroundColor: "#ffffff" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <h3 style={{ margin: 0 }}>Interview Review</h3>
            <button
              onClick={() => setReviewSession(null)}
              style={{
                padding: "6px 10px",
                backgroundColor: "#e5e7eb",
                color: "#111827",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              Close
            </button>
          </div>
          <p style={{ marginTop: 0, color: "#6b7280" }}>
            Final Score: {reviewSession.final_score ?? 0}/10
          </p>
          {reviewSession.questions && reviewSession.questions.length > 0 && (
            <div style={{ display: "grid", gap: "12px" }}>
              {reviewSession.questions.map((q) => {
                const answer = (reviewSession.answers || []).find((a) => a.question_id === q.id) || {};
                return (
                  <div key={q.id} style={{ border: "1px solid #e5e7eb", borderRadius: "8px", padding: "12px" }}>
                    <div style={{ fontWeight: "600", color: "#111827", marginBottom: "6px" }}>
                      Q: {q.question_text}
                    </div>
                    <div style={{ fontSize: "14px", color: "#374151", marginBottom: "6px" }}>
                      <strong>Answer:</strong> {answer.answer_text || "No answer recorded."}
                    </div>
                    {answer.feedback_json && (
                      <div style={{ fontSize: "13px", color: "#374151" }}>
                        <strong>Feedback:</strong>{" "}
                        {typeof answer.feedback_json === "string"
                          ? answer.feedback_json
                          : JSON.stringify(answer.feedback_json)}
                      </div>
                    )}
                    {answer.score !== undefined && (
                      <div style={{ fontSize: "12px", color: "#6b7280", marginTop: "6px" }}>
                        Score: {answer.score}/10
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
=======
    </div>
  );
}
>>>>>>> upstream/main
