import React, { useState } from "react";
import {
  uploadResume,
  startInterview,
  submitAnswer,
  generateCaseStudy,
  fetchProjectKnowledge
} from "./api/client";

export default function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [interviewSession, setInterviewSession] = useState(null);
  const [answerInput, setAnswerInput] = useState("");
  const [caseStudy, setCaseStudy] = useState(null);
  const [error, setError] = useState(null);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const data = await uploadResume(file);
      setProjects(data.projects || []);
      if (data.projects && data.projects.length > 0) {
        setSelectedProject(data.projects[0]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStartInterview = async (proj) => {
    setLoading(true);
    setError(null);
    try {
      setSelectedProject(proj);
      const session = await startInterview(proj.id);
      setInterviewSession(session);
      setCaseStudy(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitAnswer = async () => {
    if (!interviewSession?.current_question || !answerInput.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await submitAnswer(
        selectedProject.id,
        interviewSession.current_question.exchange_id,
        answerInput
      );
      setInterviewSession(updated);
      setAnswerInput("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateCaseStudy = async () => {
    if (!selectedProject) return;
    setLoading(true);
    setError(null);
    try {
      const cs = await generateCaseStudy(selectedProject.id);
      setCaseStudy(cs);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <header>
        <h1>Resume-to-Technical-Case-Study</h1>
        <p className="subtitle">
          Adaptive interview engine & factual case-study generation system
        </p>
      </header>

      {error && (
        <div className="card" style={{ borderColor: "#ef4444", color: "#f87171" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Step 1: Upload Resume */}
      <section className="card">
        <h2>1. Upload Resume</h2>
        <p style={{ color: "#94a3b8", fontSize: "0.9rem" }}>
          Upload any PDF, DOCX, or text resume. The system uses layout-aware parsing and semantic extraction.
        </p>
        <form onSubmit={handleUpload} style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={(e) => setFile(e.target.files[0])}
          />
          <button type="submit" className="btn" disabled={!file || loading}>
            {loading ? "Processing..." : "Extract Projects"}
          </button>
        </form>
      </section>

      {/* Step 2: Detected Projects */}
      {projects.length > 0 && (
        <section className="card">
          <h2>2. Detected Projects ({projects.length})</h2>
          {projects.map((p) => (
            <div
              key={p.id}
              className={`project-item ${selectedProject?.id === p.id ? "selected" : ""}`}
            >
              <div>
                <h3 style={{ margin: "0 0 0.3rem 0", color: "#fff" }}>{p.name}</h3>
                <p style={{ margin: "0 0 0.5rem 0", color: "#94a3b8", fontSize: "0.85rem" }}>
                  {p.description || "No description extracted."}
                </p>
                <div>
                  {(p.technologies || []).map((t, idx) => (
                    <span key={idx} className="tag">{t}</span>
                  ))}
                </div>
              </div>
              <div>
                <button
                  className="btn"
                  onClick={() => handleStartInterview(p)}
                  disabled={loading}
                >
                  Select & Interview
                </button>
              </div>
            </div>
          ))}
        </section>
      )}

      {/* Step 3: Adaptive Interview */}
      {interviewSession && selectedProject && (
        <section className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2>3. Adaptive Interview: {selectedProject.name}</h2>
            <span style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
              Round {interviewSession.round_count}
            </span>
          </div>

          {/* Coverage Overview */}
          <div style={{ margin: "1rem 0", display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            {Object.entries(interviewSession.coverage || {}).map(([area, state]) => (
              <span key={area} className={`coverage-pill cov-${state}`}>
                {area}: {state}
              </span>
            ))}
          </div>

          {interviewSession.current_question ? (
            <div style={{ marginTop: "1.5rem" }}>
              <div style={{ background: "#090d16", padding: "1rem", borderRadius: "6px", borderLeft: "4px solid #38bdf8" }}>
                <span style={{ color: "#38bdf8", fontWeight: "bold", fontSize: "0.8rem", textTransform: "uppercase" }}>
                  Target: {interviewSession.current_question.target_area}
                </span>
                <p style={{ margin: "0.5rem 0 0 0", fontSize: "1.05rem" }}>
                  {interviewSession.current_question.question}
                </p>
                {interviewSession.current_question.rationale && (
                  <p style={{ margin: "0.5rem 0 0 0", color: "#64748b", fontSize: "0.8rem" }}>
                    <em>Rationale: {interviewSession.current_question.rationale}</em>
                  </p>
                )}
              </div>

              <div style={{ marginTop: "1rem" }}>
                <label style={{ fontSize: "0.85rem", color: "#94a3b8" }}>Your Response:</label>
                <textarea
                  value={answerInput}
                  onChange={(e) => setAnswerInput(e.target.value)}
                  placeholder="Provide technical specifics, decisions, tradeoffs, or challenges..."
                />
                <div style={{ marginTop: "0.75rem" }}>
                  <button
                    className="btn"
                    onClick={handleSubmitAnswer}
                    disabled={!answerInput.trim() || loading}
                  >
                    {loading ? "Evaluating..." : "Submit Answer"}
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={handleGenerateCaseStudy}
                    disabled={loading}
                  >
                    Finish & Generate Now
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div style={{ marginTop: "1rem" }}>
              <p style={{ color: "#34d399", fontWeight: "600" }}>
                ✓ Interview complete! {interviewSession.stop_reason}
              </p>
              <button
                className="btn"
                onClick={handleGenerateCaseStudy}
                disabled={loading}
              >
                {loading ? "Generating..." : "Generate Technical Case Study"}
              </button>
            </div>
          )}
        </section>
      )}

      {/* Step 4: Final Technical Case Study */}
      {caseStudy && (
        <section className="card">
          <h2>4. Technical Case Study</h2>
          <pre>{caseStudy.markdown_content}</pre>
        </section>
      )}
    </div>
  );
}
