import React, { useState, useEffect, useMemo } from "react";
import {
  fetchDashboard,
  deleteProject,
  deleteResume,
  reExtractResume,
  getCaseStudyExportUrl
} from "../api/client";

export default function DashboardView({
  currentUser,
  onSelectProjectForInterview,
  onSelectProjectForCaseStudy,
  onStartNewUpload,
  onOpenAuth
}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("projects"); // "projects" | "resumes" | "archive"

  // Filter & Search states
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all"); // "all" | "completed" | "in_progress" | "not_started"
  const [techFilter, setTechFilter] = useState("");

  // Re-extraction & action states
  const [reExtractingId, setReExtractingId] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);

  // Transcript & Preview Modals
  const [viewTranscriptProject, setViewTranscriptProject] = useState(null);
  const [previewCaseStudy, setPreviewCaseStudy] = useState(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchDashboard();
      setData(res);
    } catch (err) {
      setError(err.message || "Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [currentUser]);

  // Handle Project Deletion
  const handleDeleteProject = async (projectId, e) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this project? This will also remove its interview and case studies.")) {
      return;
    }
    try {
      await deleteProject(projectId);
      setActionSuccess("Project deleted successfully.");
      setTimeout(() => setActionSuccess(null), 3000);
      loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  // Handle Resume Deletion
  const handleDeleteResume = async (resumeId, e) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this resume? All associated projects will be removed.")) {
      return;
    }
    try {
      await deleteResume(resumeId);
      setActionSuccess("Resume document deleted successfully.");
      setTimeout(() => setActionSuccess(null), 3000);
      loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  // Handle Resume Re-extraction
  const handleReExtract = async (resumeId, e) => {
    e.stopPropagation();
    setReExtractingId(resumeId);
    setError(null);
    try {
      const res = await reExtractResume(resumeId);
      setActionSuccess(res.message || "Projects re-extracted successfully!");
      setTimeout(() => setActionSuccess(null), 4000);
      loadData();
    } catch (err) {
      setError(err.message);
    } finally {
      setReExtractingId(null);
    }
  };

  // Filtered projects
  const filteredProjects = useMemo(() => {
    if (!data?.projects) return [];
    return data.projects.filter((p) => {
      const matchesSearch =
        searchQuery === "" ||
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (p.description && p.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (p.technologies && p.technologies.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase())));

      let matchesStatus = true;
      const status = p.interview?.status || "not_started";
      if (statusFilter !== "all") {
        matchesStatus = status === statusFilter;
      }

      let matchesTech = true;
      if (techFilter) {
        matchesTech = p.technologies && p.technologies.includes(techFilter);
      }

      return matchesSearch && matchesStatus && matchesTech;
    });
  }, [data?.projects, searchQuery, statusFilter, techFilter]);

  // Unique tech tags across all projects
  const allTechs = useMemo(() => {
    if (!data?.projects) return [];
    const set = new Set();
    data.projects.forEach((p) => {
      (p.technologies || []).forEach((t) => set.add(t));
    });
    return Array.from(set).slice(0, 16);
  }, [data?.projects]);

  if (loading) {
    return (
      <div className="dashboard-loading-container">
        <div className="auth-spinner" style={{ width: "32px", height: "32px", borderWidth: "3px" }} />
        <p>Loading your personal dashboard...</p>
      </div>
    );
  }

  const stats = data?.stats || { total_resumes: 0, total_projects: 0, completed_interviews: 0, total_case_studies: 0 };

  return (
    <div className="dashboard-view-container">
      {/* ─── Hero / Header ─── */}
      <div className="dashboard-header-card">
        <div className="dashboard-header-info">
          <div className="dashboard-header-badge">
            <span className="auth-modal-badge-dot" />
            Personal Engineering Portfolio
          </div>
          <h1 className="dashboard-title">
            {currentUser?.full_name ? `Welcome back, ${currentUser.full_name}` : "Your Personal Dashboard"}
          </h1>
          <p className="dashboard-subtitle">
            Manage your uploaded resumes, resume adaptive interviews, and download publication-ready case studies.
          </p>
        </div>

        <div className="dashboard-header-cta">
          <button type="button" className="btn btn-primary" onClick={onStartNewUpload}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Upload New Resume
          </button>
        </div>
      </div>

      {/* Action Notification Banner */}
      {actionSuccess && (
        <div className="dashboard-alert-banner success">
          <span>✓</span>
          <span>{actionSuccess}</span>
        </div>
      )}

      {error && (
        <div className="dashboard-alert-banner error">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* ─── KPI Metric Cards ─── */}
      <div className="dashboard-stats-grid">
        <div className="stat-card">
          <div className="stat-card-icon blue">📄</div>
          <div className="stat-card-val">{stats.total_resumes}</div>
          <div className="stat-card-lbl">Resumes Uploaded</div>
        </div>

        <div className="stat-card">
          <div className="stat-card-icon purple">🚀</div>
          <div className="stat-card-val">{stats.total_projects}</div>
          <div className="stat-card-lbl">Extracted Projects</div>
        </div>

        <div className="stat-card">
          <div className="stat-card-icon green">🎯</div>
          <div className="stat-card-val">{stats.completed_interviews}</div>
          <div className="stat-card-lbl">Interviews Completed</div>
        </div>

        <div className="stat-card">
          <div className="stat-card-icon amber">📑</div>
          <div className="stat-card-val">{stats.total_case_studies}</div>
          <div className="stat-card-lbl">Case Studies Generated</div>
        </div>
      </div>

      {/* ─── Tab Navigation Bar ─── */}
      <div className="dashboard-nav-tabs">
        <button
          type="button"
          className={`dash-tab-btn ${activeTab === "projects" ? "active" : ""}`}
          onClick={() => setActiveTab("projects")}
        >
          <span>Projects & Interviews</span>
          <span className="dash-tab-count">{data?.projects?.length || 0}</span>
        </button>

        <button
          type="button"
          className={`dash-tab-btn ${activeTab === "resumes" ? "active" : ""}`}
          onClick={() => setActiveTab("resumes")}
        >
          <span>Resume History</span>
          <span className="dash-tab-count">{data?.resumes?.length || 0}</span>
        </button>

        <button
          type="button"
          className={`dash-tab-btn ${activeTab === "archive" ? "active" : ""}`}
          onClick={() => setActiveTab("archive")}
        >
          <span>Case Study Archive</span>
          <span className="dash-tab-count">{data?.case_studies?.length || 0}</span>
        </button>
      </div>

      {/* ═══════════════════════════════════════════
          TAB 1: Projects & Interviews
          ═══════════════════════════════════════════ */}
      {activeTab === "projects" && (
        <div className="dashboard-tab-content">
          {/* Controls: Search & Filters */}
          <div className="dashboard-filter-bar">
            <div className="dashboard-search-box">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                type="text"
                placeholder="Search projects by name, keyword, or tech..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="dashboard-search-input"
              />
              {searchQuery && (
                <button type="button" className="dashboard-clear-btn" onClick={() => setSearchQuery("")}>
                  ✕
                </button>
              )}
            </div>

            <div className="dashboard-status-pills">
              <button
                type="button"
                className={`dash-filter-pill ${statusFilter === "all" ? "active" : ""}`}
                onClick={() => setStatusFilter("all")}
              >
                All Statuses
              </button>
              <button
                type="button"
                className={`dash-filter-pill ${statusFilter === "completed" ? "active" : ""}`}
                onClick={() => setStatusFilter("completed")}
              >
                Completed
              </button>
              <button
                type="button"
                className={`dash-filter-pill ${statusFilter === "in_progress" ? "active" : ""}`}
                onClick={() => setStatusFilter("in_progress")}
              >
                In Interview
              </button>
              <button
                type="button"
                className={`dash-filter-pill ${statusFilter === "not_started" ? "active" : ""}`}
                onClick={() => setStatusFilter("not_started")}
              >
                Not Started
              </button>
            </div>
          </div>

          {/* Quick Tech Tag Filters */}
          {allTechs.length > 0 && (
            <div className="dashboard-tech-row">
              <span className="dash-tech-label">Filter Tech:</span>
              {techFilter && (
                <button
                  type="button"
                  className="dash-tech-tag active"
                  onClick={() => setTechFilter("")}
                >
                  ✕ Clear ({techFilter})
                </button>
              )}
              {allTechs.map((t) => (
                <button
                  key={t}
                  type="button"
                  className={`dash-tech-tag ${techFilter === t ? "active" : ""}`}
                  onClick={() => setTechFilter(techFilter === t ? "" : t)}
                >
                  {t}
                </button>
              ))}
            </div>
          )}

          {/* Projects Grid */}
          {filteredProjects.length === 0 ? (
            <div className="dashboard-empty-card">
              <div className="dashboard-empty-icon">🔍</div>
              <h3>No projects found</h3>
              <p>
                {searchQuery || statusFilter !== "all" || techFilter
                  ? "Try resetting your search or filter criteria."
                  : "Upload your first resume to automatically extract projects and conduct adaptive interviews."}
              </p>
              <button type="button" className="btn btn-primary" onClick={onStartNewUpload}>
                Upload Resume
              </button>
            </div>
          ) : (
            <div className="dashboard-projects-grid">
              {filteredProjects.map((p) => {
                const status = p.interview?.status || "not_started";
                const hasCaseStudy = p.case_studies && p.case_studies.length > 0;
                const exchangesCount = p.interview?.exchanges?.length || 0;
                const coveragePercent = p.interview?.coverage_percent || 0;
                const is100Percent = coveragePercent >= 100 || (p.interview?.fulfilled_count >= 8);

                return (
                  <div key={p.id} className="dash-project-card">
                    {/* Top Row: Origin & Status */}
                    <div className="dash-project-card-top">
                      <span className="dash-project-origin" title={p.resume_filename}>
                        📄 {p.resume_filename}
                      </span>
                      <span className={`dash-status-badge ${status}`}>
                        {status === "completed"
                          ? is100Percent
                            ? "✓ 100% Completed"
                            : `✓ Completed (${coveragePercent}%)`
                          : status === "in_progress"
                          ? `● Round ${p.interview?.round_count || 1}`
                          : "○ Not Started"}
                      </span>
                    </div>

                    {/* Title & Description */}
                    <h3 className="dash-project-title">{p.name}</h3>
                    <p className="dash-project-desc">{p.description || "No description provided."}</p>

                    {/* Tech stack */}
                    {p.technologies && p.technologies.length > 0 && (
                      <div className="dash-project-techs">
                        {p.technologies.map((t) => (
                          <span
                            key={t}
                            className="dash-tech-pill"
                            onClick={() => setTechFilter(t)}
                            title={`Filter by ${t}`}
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Interview progress bar */}
                    {status !== "not_started" && (
                      <div className="dash-interview-progress-bar-wrap">
                        <div className="dash-progress-label-row">
                          <span>Interview Coverage</span>
                          <span style={is100Percent ? { color: "#34d399", fontWeight: 700 } : {}}>
                            {is100Percent ? "100%" : `${coveragePercent}%`}
                          </span>
                        </div>
                        <div className="dash-progress-track">
                          <div
                            className="dash-progress-fill"
                            style={{
                              width: `${is100Percent ? 100 : coveragePercent}%`,
                              background: is100Percent ? "linear-gradient(90deg, #10b981, #34d399)" : undefined
                            }}
                          />
                        </div>
                      </div>
                    )}

                    {/* Case study variants available */}
                    {hasCaseStudy && (
                      <div className="dash-case-study-pills">
                        <span className="cs-pill-label">Generated:</span>
                        {p.case_studies.map((cs) => (
                          <span key={cs.id} className="cs-available-tag">
                            {cs.variant_type === "client_brochure" ? "💼 Brochure" : "🛠️ Technical"}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Card Actions */}
                    <div className="dash-project-card-actions">
                      {hasCaseStudy ? (
                        <button
                          type="button"
                          className="btn btn-primary btn-sm"
                          onClick={() => onSelectProjectForCaseStudy(p)}
                        >
                          View Case Study
                        </button>
                      ) : is100Percent ? (
                        <button
                          type="button"
                          className="btn btn-primary btn-sm"
                          onClick={() => onSelectProjectForInterview(p)}
                        >
                          Generate Case Study
                        </button>
                      ) : status === "in_progress" || (status === "completed" && !is100Percent) ? (
                        <button
                          type="button"
                          className="btn btn-primary btn-sm"
                          onClick={() => onSelectProjectForInterview(p)}
                        >
                          Resume Interview
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => onSelectProjectForInterview(p)}
                        >
                          Start Interview
                        </button>
                      )}

                      {exchangesCount > 0 && (
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          onClick={() => setViewTranscriptProject(p)}
                          title="Review interview Q&A transcript"
                        >
                          Transcript ({exchangesCount})
                        </button>
                      )}

                      <button
                        type="button"
                        className="dash-delete-icon-btn"
                        onClick={(e) => handleDeleteProject(p.id, e)}
                        title="Delete project"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ═══════════════════════════════════════════
          TAB 2: Resume History
          ═══════════════════════════════════════════ */}
      {activeTab === "resumes" && (
        <div className="dashboard-tab-content">
          {!data?.resumes || data.resumes.length === 0 ? (
            <div className="dashboard-empty-card">
              <div className="dashboard-empty-icon">📄</div>
              <h3>No resumes uploaded yet</h3>
              <p>Upload a resume to automatically extract projects and conduct technical interviews.</p>
              <button type="button" className="btn btn-primary" onClick={onStartNewUpload}>
                Upload Your First Resume
              </button>
            </div>
          ) : (
            <div className="dashboard-resumes-list">
              {data.resumes.map((r) => {
                const isReExtracting = reExtractingId === r.id;
                return (
                  <div key={r.id} className="dash-resume-card">
                    <div className="dash-resume-icon-wrap">
                      <span className="dash-resume-icon">
                        {r.file_type === "pdf" ? "📕" : r.file_type === "docx" ? "📘" : "📄"}
                      </span>
                    </div>

                    <div className="dash-resume-details">
                      <div className="dash-resume-title-row">
                        <h4 className="dash-resume-filename">{r.filename}</h4>
                        <span className="dash-resume-type-badge">{r.file_type.toUpperCase()}</span>
                      </div>
                      <div className="dash-resume-meta">
                        <span>Uploaded: {r.created_at ? new Date(r.created_at).toLocaleDateString() : "Recent"}</span>
                        <span>•</span>
                        <span>{r.projects_count} project(s) extracted</span>
                      </div>
                    </div>

                    <div className="dash-resume-actions">
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={(e) => handleReExtract(r.id, e)}
                        disabled={isReExtracting}
                      >
                        {isReExtracting ? "Re-extracting..." : "🔄 Re-extract"}
                      </button>
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm text-danger"
                        onClick={(e) => handleDeleteResume(r.id, e)}
                        title="Delete resume and projects"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ═══════════════════════════════════════════
          TAB 3: Case Study Archive
          ═══════════════════════════════════════════ */}
      {activeTab === "archive" && (
        <div className="dashboard-tab-content">
          {!data?.case_studies || data.case_studies.length === 0 ? (
            <div className="dashboard-empty-card">
              <div className="dashboard-empty-icon">📑</div>
              <h3>No case studies generated yet</h3>
              <p>Complete an interview round for any project to generate Technical Case Studies and Client Brochures.</p>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setActiveTab("projects")}
              >
                Go to Projects
              </button>
            </div>
          ) : (
            <div className="dashboard-archive-grid">
              {data.case_studies.map((cs) => {
                const isBrochure = cs.variant_type === "client_brochure";
                return (
                  <div key={cs.id} className="dash-archive-card">
                    <div className="dash-archive-header">
                      <span className={`dash-variant-pill ${isBrochure ? "brochure" : "technical"}`}>
                        {isBrochure ? "💼 Client Brochure" : "🛠️ Technical Case Study"}
                      </span>
                      <span className="dash-archive-date">
                        {cs.created_at ? new Date(cs.created_at).toLocaleDateString() : ""}
                      </span>
                    </div>

                    <h4 className="dash-archive-title">{cs.title}</h4>
                    <p className="dash-archive-project-name">Project: {cs.project_name}</p>

                    <div className="dash-archive-actions">
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => setPreviewCaseStudy(cs)}
                      >
                        👁️ Preview
                      </button>

                      <a
                        href={getCaseStudyExportUrl(cs.project_id, "pdf", cs.variant_type)}
                        download
                        className="btn btn-ghost btn-sm"
                        title="Download formatted PDF"
                      >
                        📥 PDF
                      </a>

                      <a
                        href={getCaseStudyExportUrl(cs.project_id, "docx", cs.variant_type)}
                        download
                        className="btn btn-ghost btn-sm"
                        title="Download Word Document"
                      >
                        📥 DOCX
                      </a>

                      <a
                        href={getCaseStudyExportUrl(cs.project_id, "md", cs.variant_type)}
                        download
                        className="btn btn-ghost btn-sm"
                        title="Download Markdown"
                      >
                        MD
                      </a>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ═══════════════════════════════════════════
          MODAL: Interview Transcript Review
          ═══════════════════════════════════════════ */}
      {viewTranscriptProject && (
        <div className="auth-modal-backdrop" onClick={() => setViewTranscriptProject(null)}>
          <div className="dashboard-transcript-modal" onClick={(e) => e.stopPropagation()}>
            <div className="transcript-modal-header">
              <div>
                <span className="auth-modal-badge">
                  <span className="auth-modal-badge-dot" />
                  Interview Transcript
                </span>
                <h3 className="transcript-modal-title">{viewTranscriptProject.name}</h3>
              </div>
              <button
                type="button"
                className="auth-modal-close"
                onClick={() => setViewTranscriptProject(null)}
              >
                ✕
              </button>
            </div>

            <div className="transcript-modal-body">
              {viewTranscriptProject.interview?.exchanges?.map((ex, idx) => (
                <div key={ex.id || idx} className="transcript-exchange-item">
                  <div className="transcript-q-bubble">
                    <span className="transcript-speaker">🤖 AI Technical Lead ({ex.target_area})</span>
                    <p className="transcript-text">{ex.question}</p>
                  </div>
                  <div className="transcript-a-bubble">
                    <span className="transcript-speaker">👤 Your Response</span>
                    <p className="transcript-text">{ex.answer || "(No response recorded yet)"}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="transcript-modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setViewTranscriptProject(null)}
              >
                Close
              </button>
              {!(viewTranscriptProject?.interview?.coverage_percent >= 100 || viewTranscriptProject?.interview?.fulfilled_count >= 8) ? (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => {
                    const proj = viewTranscriptProject;
                    setViewTranscriptProject(null);
                    onSelectProjectForInterview(proj);
                  }}
                >
                  Resume Interview →
                </button>
              ) : (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => {
                    const proj = viewTranscriptProject;
                    setViewTranscriptProject(null);
                    if (proj.case_studies && proj.case_studies.length > 0) {
                      onSelectProjectForCaseStudy(proj);
                    } else {
                      onSelectProjectForInterview(proj);
                    }
                  }}
                >
                  {viewTranscriptProject.case_studies && viewTranscriptProject.case_studies.length > 0 ? "View Case Study →" : "Generate Case Study →"}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════
          MODAL: Quick Case Study Preview
          ═══════════════════════════════════════════ */}
      {previewCaseStudy && (
        <div className="auth-modal-backdrop" onClick={() => setPreviewCaseStudy(null)}>
          <div className="dashboard-transcript-modal preview-modal" onClick={(e) => e.stopPropagation()}>
            <div className="transcript-modal-header">
              <div>
                <span className="auth-modal-badge">
                  <span className="auth-modal-badge-dot" />
                  {previewCaseStudy.variant_type === "client_brochure" ? "Client Brochure" : "Technical Case Study"}
                </span>
                <h3 className="transcript-modal-title">{previewCaseStudy.title}</h3>
              </div>
              <button
                type="button"
                className="auth-modal-close"
                onClick={() => setPreviewCaseStudy(null)}
              >
                ✕
              </button>
            </div>

            <div className="transcript-modal-body markdown-preview-body">
              <pre className="dashboard-markdown-pre">
                {previewCaseStudy.markdown_content}
              </pre>
            </div>

            <div className="transcript-modal-footer">
              <a
                href={getCaseStudyExportUrl(previewCaseStudy.project_id, "pdf", previewCaseStudy.variant_type)}
                download
                className="btn btn-primary btn-sm"
              >
                Download PDF
              </a>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setPreviewCaseStudy(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
