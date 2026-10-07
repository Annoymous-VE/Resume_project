import React, { useState, useRef, useEffect } from "react";
import {
  uploadResume,
  createProject,
  startInterview,
  submitAnswer,
  continueInterview,
  generateCaseStudy,
  fetchCaseStudy,
  fetchAllCaseStudies,
  getCaseStudyExportUrl,
  getStoredUser,
  fetchCurrentUser,
  logoutUser
} from "./api/client";
import LandingPage from "./LandingPage";
import Navbar from "./components/Navbar";
import AuthModal from "./components/AuthModal";
import DashboardView from "./components/DashboardView";

function renderInline(text) {
  const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={i}
          style={{
            background: "#1e293b",
            padding: "0.15rem 0.35rem",
            borderRadius: "3px",
            color: "#38bdf8",
            fontSize: "0.9em"
          }}
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

function MarkdownRenderer({ content }) {
  const lines = (content || "").split("\n");
  const elements = [];
  let currentBullets = [];

  const flushBullets = () => {
    if (currentBullets.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="cs-bullet-list">
          {currentBullets.map((b, idx) => (
            <li key={idx} style={{ whiteSpace: "pre-line" }}>{renderInline(b)}</li>
          ))}
        </ul>
      );
      currentBullets = [];
    }
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushBullets();
      return;
    }

    if (trimmed.startsWith("# ")) {
      flushBullets();
      elements.push(
        <h1 key={`h1-${idx}`} className="cs-title">
          {renderInline(trimmed.replace(/^#\s*/, ""))}
        </h1>
      );
    } else if (trimmed.startsWith("## ")) {
      flushBullets();
      elements.push(
        <h2 key={`h2-${idx}`} className="cs-h2">
          {renderInline(trimmed.replace(/^##\s*/, ""))}
        </h2>
      );
    } else if (trimmed.startsWith("### ")) {
      flushBullets();
      elements.push(
        <h3 key={`h3-${idx}`} className="cs-h3">
          {renderInline(trimmed.replace(/^###\s*/, ""))}
        </h3>
      );
    } else if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      currentBullets.push(trimmed.replace(/^[-*]\s*/, ""));
    } else if ((line.startsWith("  ") || line.startsWith("\t")) && currentBullets.length > 0) {
      currentBullets[currentBullets.length - 1] += "\n" + trimmed;
    } else if (trimmed.startsWith(">")) {
      flushBullets();
      elements.push(
        <blockquote key={`quote-${idx}`} className="cs-callout">
          {renderInline(trimmed.replace(/^>\s*/, ""))}
        </blockquote>
      );
    } else {
      flushBullets();
      elements.push(
        <p key={`p-${idx}`} className="cs-p">
          {renderInline(trimmed)}
        </p>
      );
    }
  });

  flushBullets();
  return <div className="case-study-reader">{elements}</div>;
}

/* ─── Stepper Steps Configuration ─── */
const STEPS = [
  { num: 1, label: "Upload Resume" },
  { num: 2, label: "Select Project" },
  { num: 3, label: "Interview" },
  { num: 4, label: "Case Study & Brochure" },
];

function StepperBar({ currentStep }) {
  return (
    <div className="stepper-bar">
      <div className="stepper-inner">
        {STEPS.map((step, idx) => {
          const isCompleted = currentStep > step.num;
          const isActive = currentStep === step.num;
          const stateClass = isCompleted ? "completed" : isActive ? "active" : "upcoming";

          return (
            <React.Fragment key={step.num}>
              {idx > 0 && (
                <div className={`stepper-connector ${isCompleted ? "completed" : currentStep >= step.num ? "active" : ""}`} />
              )}
              <div className={`stepper-step ${stateClass}`}>
                <div className="stepper-circle">
                  {isCompleted ? (
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                      <path d="M3 8.5L6.5 12L13 4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  ) : (
                    step.num
                  )}
                </div>
                <span className="stepper-label">{step.label}</span>
              </div>
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

export default function App() {
  // Authentication States
  const [currentUser, setCurrentUser] = useState(() => getStoredUser());
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState("login");
  const [viewMode, setViewMode] = useState("wizard"); // "wizard" | "dashboard"

  const [file, setFile] = useState(null);
  const [resumeId, setResumeId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generatingCaseStudy, setGeneratingCaseStudy] = useState(false);
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [interviewSession, setInterviewSession] = useState(null);
  const [answerInput, setAnswerInput] = useState("");
  const [pendingAnswer, setPendingAnswer] = useState(null);
  const [caseStudy, setCaseStudy] = useState(null);
  const [error, setError] = useState(null);
  const [showRawMarkdown, setShowRawMarkdown] = useState(false);

  // Audience format states (Technical Case Study vs. Client Brochure)
  const [activeVariant, setActiveVariant] = useState("technical");
  const [caseStudiesMap, setCaseStudiesMap] = useState({ technical: null, client_brochure: null });
  const [isCaseStudyStep, setIsCaseStudyStep] = useState(false);
  const [generatingVariant, setGeneratingVariant] = useState(null);
  const [loadingVariant, setLoadingVariant] = useState(false);

  // States for manual unlisted project creation
  const [showAddProjectModal, setShowAddProjectModal] = useState(false);
  const [addProjectForm, setAddProjectForm] = useState({
    name: "",
    description: "",
    technologies: "",
    contributions: "",
    outcomes: "",
    links: ""
  });
  const [addingProject, setAddingProject] = useState(false);
  const [addProjectError, setAddProjectError] = useState(null);

  const chatEndRef = useRef(null);
  const caseStudyRef = useRef(null);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [interviewSession?.exchanges, interviewSession?.current_question, loading, pendingAnswer]);

  useEffect(() => {
    if (caseStudy && caseStudyRef.current) {
      caseStudyRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [caseStudy]);

  // Verify authenticated session on mount
  useEffect(() => {
    fetchCurrentUser()
      .then((user) => {
        if (user) setCurrentUser(user);
      })
      .catch(() => {});
  }, []);

  const handleOpenAuth = (mode = "login") => {
    setAuthModalMode(mode);
    setIsAuthModalOpen(true);
  };

  const handleCloseAuth = () => {
    setIsAuthModalOpen(false);
  };

  const resetWizardState = () => {
    setFile(null);
    setResumeId(null);
    setProjects([]);
    setSelectedProject(null);
    setInterviewSession(null);
    setAnswerInput("");
    setPendingAnswer(null);
    setCaseStudy(null);
    setError(null);
    setActiveVariant("technical");
    setCaseStudiesMap({ technical: null, client_brochure: null });
    setIsCaseStudyStep(false);
    setGeneratingVariant(null);
    setLoadingVariant(false);
    setShowAddProjectModal(false);
    setViewMode("wizard");
  };

  const handleAuthSuccess = (user) => {
    resetWizardState();
    setCurrentUser(user);
    setIsAuthModalOpen(false);
  };

  const handleLogout = () => {
    logoutUser();
    resetWizardState();
    setCurrentUser(null);
  };

  const handleResetToHome = () => {
    resetWizardState();
  };

  const handleDashboardSelectInterview = async (proj) => {
    setViewMode("wizard");
    await handleStartInterview(proj);
  };

  const handleDashboardSelectCaseStudy = async (proj) => {
    setLoading(true);
    setError(null);
    setSelectedProject(proj);
    try {
      const existingList = await fetchAllCaseStudies(proj.id);
      if (Array.isArray(existingList) && existingList.length > 0) {
        const map = { technical: null, client_brochure: null };
        existingList.forEach((item) => {
          if (item.variant_type) map[item.variant_type] = item;
        });
        setCaseStudiesMap(map);
        const chosen = map.technical || map.client_brochure || existingList[0];
        setCaseStudy(chosen);
        setActiveVariant(chosen.variant_type || "technical");
      }
      setIsCaseStudyStep(true);
      setViewMode("wizard");
    } catch (err) {
      setError(err.message || "Failed to load case studies for project.");
    } finally {
      setLoading(false);
    }
  };

  const handleDashboardStartNewUpload = () => {
    resetWizardState();
  };

  /* ─── Derived wizard step ─── */
  const currentStep = isCaseStudyStep
    ? 4
    : interviewSession && selectedProject
      ? 3
      : (projects.length > 0 || resumeId)
        ? 2
        : 1;

  const goBackToStep = (step) => {
    if (step === 1) {
      resetWizardState();
    } else if (step === 2) {
      setIsCaseStudyStep(false);
      setCaseStudy(null);
      setCaseStudiesMap({ technical: null, client_brochure: null });
      setInterviewSession(null);
    } else if (step === 3) {
      setIsCaseStudyStep(false);
    }
  };

  const isStopPhrase = (text) => {
    if (!text) return false;
    const clean = text.trim().toLowerCase().replace(/[.!,?]+$/, "").trim();
    const stopPhrases = [
      "i have nothing more to add",
      "nothing more to add",
      "i have nothing to add",
      "nothing to add",
      "i don't have anything more to add",
      "i dont have anything more to add",
      "i do not have anything more to add",
      "i have nothing else to add",
      "nothing else to add",
      "nothing more",
      "no more to add",
    ];
    return (
      stopPhrases.includes(clean) ||
      clean.startsWith("i have nothing more to add") ||
      clean.startsWith("nothing more to add")
    );
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    if (!currentUser) {
      handleOpenAuth("login");
      setError("Please sign in or create an account to upload your resume.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await uploadResume(file);
      setResumeId(data.resume_id || null);
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

  const handleOpenAddProjectModal = () => {
    setAddProjectForm({
      name: "",
      description: "",
      technologies: "",
      contributions: "",
      outcomes: "",
      links: ""
    });
    setAddProjectError(null);
    setShowAddProjectModal(true);
  };

  const handleCloseAddProjectModal = () => {
    if (addingProject) return;
    setShowAddProjectModal(false);
    setAddProjectError(null);
  };

  const handleAddProjectSubmit = async (e) => {
    e.preventDefault();
    const trimmedName = addProjectForm.name.trim();
    const trimmedDesc = addProjectForm.description.trim();

    if (!trimmedName) {
      setAddProjectError("Project Name is mandatory.");
      return;
    }
    if (!trimmedDesc) {
      setAddProjectError("Project Description / Problem Statement is mandatory.");
      return;
    }

    const parsedTechs = addProjectForm.technologies
      .split(/[,;\n]+/)
      .map((t) => t.trim())
      .filter(Boolean);

    if (parsedTechs.length === 0) {
      setAddProjectError("At least one Technology is mandatory (e.g. React, Python).");
      return;
    }

    const parsedContribs = addProjectForm.contributions
      .split(/\n+/)
      .map((c) => c.replace(/^[-*•]\s*/, "").trim())
      .filter(Boolean);

    const parsedOutcomes = addProjectForm.outcomes
      .split(/\n+/)
      .map((o) => o.replace(/^[-*•]\s*/, "").trim())
      .filter(Boolean);

    const parsedLinks = addProjectForm.links
      .split(/[,;\n]+/)
      .map((l) => l.trim())
      .filter(Boolean);

    setAddingProject(true);
    setAddProjectError(null);

    try {
      const payload = {
        resume_id: resumeId,
        name: trimmedName,
        description: trimmedDesc,
        technologies: parsedTechs,
        contributions: parsedContribs,
        outcomes: parsedOutcomes,
        links: parsedLinks
      };

      const newProject = await createProject(payload);
      newProject.isManual = true;

      setProjects((prev) => [newProject, ...prev]);
      setSelectedProject(newProject);
      if (currentStep === 1) {
        setCurrentStep(2);
      }
      setShowAddProjectModal(false);
    } catch (err) {
      setAddProjectError(err.message || "Failed to create custom project.");
    } finally {
      setAddingProject(false);
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
      setCaseStudiesMap({ technical: null, client_brochure: null });
      setActiveVariant("technical");
      setIsCaseStudyStep(false);
      setAnswerInput("");
      setPendingAnswer(null);
      setGeneratingCaseStudy(false);

      // Pre-fetch any existing case studies for this project in the background
      fetchAllCaseStudies(proj.id)
        .then((existingList) => {
          if (Array.isArray(existingList) && existingList.length > 0) {
            const map = { technical: null, client_brochure: null };
            existingList.forEach((item) => {
              if (item.variant_type) map[item.variant_type] = item;
            });
            setCaseStudiesMap(map);
          }
        })
        .catch(() => {});
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateVariant = async (variantToGenerate) => {
    if (!selectedProject) return;
    const variant = variantToGenerate || activeVariant || "technical";
    setLoading(true);
    setGeneratingCaseStudy(true);
    setGeneratingVariant(variant);
    setError(null);
    try {
      const cs = await generateCaseStudy(selectedProject.id, variant);
      setCaseStudiesMap((prev) => ({ ...prev, [variant]: cs }));
      setCaseStudy(cs);
      setActiveVariant(variant);
      setIsCaseStudyStep(true);

      // Synchronize all variants from backend
      fetchAllCaseStudies(selectedProject.id)
        .then((all) => {
          if (Array.isArray(all) && all.length > 0) {
            const map = { technical: null, client_brochure: null };
            all.forEach((item) => {
              if (item.variant_type) map[item.variant_type] = item;
            });
            map[variant] = cs;
            setCaseStudiesMap(map);
          }
        })
        .catch(() => {});
    } catch (err) {
      setError(err.message || `Failed to generate ${variant === "client_brochure" ? "client brochure" : "case study"}.`);
    } finally {
      setLoading(false);
      setGeneratingCaseStudy(false);
      setGeneratingVariant(null);
    }
  };

  const handleSwitchAudience = async (targetVariant) => {
    if (targetVariant === activeVariant && caseStudy) return;
    setActiveVariant(targetVariant);
    setError(null);

    // If already loaded in our local map:
    if (caseStudiesMap[targetVariant]) {
      setCaseStudy(caseStudiesMap[targetVariant]);
      return;
    }

    // Try fetching from backend if not yet in state
    if (selectedProject?.id) {
      setLoadingVariant(true);
      try {
        const existing = await fetchCaseStudy(selectedProject.id, targetVariant);
        if (existing && existing.markdown_content) {
          setCaseStudiesMap((prev) => ({ ...prev, [targetVariant]: existing }));
          setCaseStudy(existing);
        } else {
          setCaseStudy(null);
        }
      } catch {
        setCaseStudy(null);
      } finally {
        setLoadingVariant(false);
      }
    } else {
      setCaseStudy(null);
    }
  };

  const handleSubmitAnswer = async (overrideText = null) => {
    const textToSend = typeof overrideText === "string" ? overrideText : answerInput;
    if (!interviewSession?.current_question || !textToSend.trim()) return;

    const trimmed = textToSend.trim();
    const shouldStopAndGenerate = isStopPhrase(trimmed);

    // Optimistically show user's response immediately in the chat feed
    setPendingAnswer(trimmed);
    setAnswerInput("");
    setLoading(true);
    setError(null);
    if (shouldStopAndGenerate) {
      setGeneratingCaseStudy(true);
      setGeneratingVariant("technical");
    }

    try {
      const updated = await submitAnswer(
        selectedProject.id,
        interviewSession.current_question.exchange_id,
        trimmed
      );
      setInterviewSession(updated);
      setPendingAnswer(null);

      // If user indicated "I have nothing more to add", automatically proceed for case study generation
      if (shouldStopAndGenerate) {
        setGeneratingCaseStudy(true);
        setGeneratingVariant("technical");
        const cs = await generateCaseStudy(selectedProject.id, "technical");
        setCaseStudiesMap((prev) => ({ ...prev, technical: cs }));
        setCaseStudy(cs);
        setActiveVariant("technical");
        setIsCaseStudyStep(true);

        fetchAllCaseStudies(selectedProject.id)
          .then((all) => {
            if (Array.isArray(all)) {
              const map = { technical: cs, client_brochure: null };
              all.forEach((item) => {
                if (item.variant_type) map[item.variant_type] = item;
              });
              map.technical = cs;
              setCaseStudiesMap(map);
            }
          })
          .catch(() => {});
      }
    } catch (err) {
      setError(err.message);
      // Restore input text so user does not lose their typed response
      setAnswerInput(trimmed);
      setPendingAnswer(null);
    } finally {
      setLoading(false);
      setGeneratingCaseStudy(false);
      setGeneratingVariant(null);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmitAnswer();
    }
  };

  const handleGenerateCaseStudy = async (variant = "technical") => {
    return handleGenerateVariant(variant);
  };

  const handleContinueInterview = async () => {
    if (!selectedProject) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await continueInterview(selectedProject.id);
      setInterviewSession(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const CRITERIA_AREAS = [
    { key: "problem", label: "Problem" },
    { key: "architecture", label: "Architecture" },
    { key: "technical_decisions", label: "Decisions" },
    { key: "challenges", label: "Challenges" },
    { key: "solutions", label: "Solutions" },
    { key: "tradeoffs", label: "Tradeoffs" },
    { key: "performance", label: "Performance" },
    { key: "impact", label: "Impact" },
  ];

  const coverage = interviewSession?.coverage || {};
  const fulfilledCount = CRITERIA_AREAS.filter((c) => coverage[c.key] === "SUFFICIENT").length;
  const progressPercent = Math.round((fulfilledCount / CRITERIA_AREAS.length) * 100);

  const allEvidence = interviewSession?.evidence || [];
  const conversationFacts = allEvidence.filter(
    (e) => e.source === "conversation" || (e.source && e.source.startsWith("user_answer"))
  );
  const resumeFacts = allEvidence.filter((e) => e.source === "resume");

  return (
    <div className="wizard-layout">
      {/* ─── Top App Navbar with Authentication ─── */}
      <Navbar
        currentUser={currentUser}
        onOpenAuth={handleOpenAuth}
        onLogout={handleLogout}
        onResetToHome={() => {
          handleResetToHome();
          setViewMode("wizard");
        }}
        viewMode={viewMode}
        onViewChange={setViewMode}
      />

      {!currentUser ? (
        <main className="landing-main-wrapper">
          <LandingPage onGetStarted={() => handleOpenAuth("register")} />
        </main>
      ) : viewMode === "dashboard" ? (
        <main className="dashboard-main-wrapper">
          <DashboardView
            currentUser={currentUser}
            onSelectProjectForInterview={handleDashboardSelectInterview}
            onSelectProjectForCaseStudy={handleDashboardSelectCaseStudy}
            onStartNewUpload={handleDashboardStartNewUpload}
            onOpenAuth={handleOpenAuth}
          />
        </main>
      ) : (
        <>
          {/* ─── Step Content Area ─── */}
          <div className="step-content">
        {/* Global Error Banner */}
        {error && (
          <div className="step-error-banner">
            <span style={{ display: "flex", alignItems: "flex-start", gap: "0.5rem" }}>
              <span style={{ fontSize: "1.1rem", lineHeight: 1.4 }}>⚠️</span>
              <span><strong style={{ color: "#f87171" }}>Error:</strong> {error}</span>
            </span>
          </div>
        )}

        {/* ═══════════════════════════════════════════
            Step 1: Upload Resume (Shown when Logged In)
            ═══════════════════════════════════════════ */}
        {currentStep === 1 && (
          <div className="step-panel step-card-centered-wrap">
            <div className="step-card-centered">
              <div className="step-icon-ring">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="12" y1="18" x2="12" y2="12"/>
                  <polyline points="9 15 12 12 15 15"/>
                </svg>
              </div>
              <h2 className="step-title">Upload Your Resume</h2>
              <p className="step-desc">
                Upload your PDF, DOCX, or text resume. The system uses layout-aware parsing and semantic extraction to detect your technical projects.
              </p>

              <form onSubmit={handleUpload} className="upload-form">
                <label className="file-drop-zone" htmlFor="resume-file-input">
                  <input
                    id="resume-file-input"
                    type="file"
                    accept=".pdf,.docx,.txt"
                    onChange={(e) => setFile(e.target.files[0])}
                    style={{ display: "none" }}
                  />
                  <div className="file-drop-icon">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="17 8 12 3 7 8"/>
                      <line x1="12" y1="3" x2="12" y2="15"/>
                    </svg>
                  </div>
                  {file ? (
                    <div className="file-selected-info">
                      <span className="file-name">📄 {file.name}</span>
                      <span className="file-size">{(file.size / 1024).toFixed(1)} KB</span>
                    </div>
                  ) : (
                    <div className="file-drop-text">
                      <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>Click to choose a file</span>
                      <span style={{ fontSize: "0.82rem" }}>PDF, DOCX, or TXT — max 10 MB</span>
                    </div>
                  )}
                </label>

                <div className="upload-actions">
                  <button type="submit" className="btn btn-lg" disabled={!file || loading}>
                    {loading ? (
                      <>
                        <span className="spinner" />
                        Processing...
                      </>
                    ) : (
                      "Extract Projects →"
                    )}
                  </button>
                  <span className="upload-or">or</span>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleOpenAddProjectModal}
                  >
                    + Add Project Manually
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════
            Step 2: Select Project
            ═══════════════════════════════════════════ */}
        {currentStep === 2 && (
          <div className="step-panel step-projects">
            <div className="step-header-bar">
              <button className="btn-back" onClick={() => goBackToStep(1)}>
                ← Back to Upload
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleOpenAddProjectModal}
                style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}
              >
                <span style={{ fontSize: "1.1rem", lineHeight: 1 }}>+</span> Add Unlisted Project
              </button>
            </div>

            <div className="step-projects-header">
              <h2 className="step-title" style={{ marginBottom: "0.25rem" }}>
                Detected Technical Projects
                <span className="project-count-badge">{projects.length}</span>
              </h2>
              <p className="step-desc">
                Select a project from your resume to begin the adaptive interview, or add an unlisted project.
              </p>
            </div>

            {projects.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">📂</div>
                <p>No technical projects detected from the resume.</p>
                <button type="button" className="btn" onClick={handleOpenAddProjectModal}>
                  + Add Unlisted Project Manually
                </button>
              </div>
            ) : (
              <div className="project-grid">
                {projects.map((p) => (
                  <div
                    key={p.id}
                    className={`project-card ${selectedProject?.id === p.id ? "selected" : ""}`}
                  >
                    <div className="project-card-body">
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.4rem" }}>
                        <h3 className="project-card-title">{p.name}</h3>
                        {(p.isManual || p.source_blocks?.includes("manual_entry")) && (
                          <span className="tag-manual">Manual</span>
                        )}
                      </div>
                      <p className="project-card-desc">
                        {p.description || "No description extracted."}
                      </p>
                      <div className="project-card-tags">
                        {p.technologies?.map((t, idx) => (
                          <span key={idx} className="tag">{t}</span>
                        ))}
                      </div>
                    </div>
                    <div className="project-card-action">
                      <button
                        className="btn"
                        onClick={() => handleStartInterview(p)}
                        disabled={loading}
                      >
                        {loading && selectedProject?.id === p.id ? (
                          <>
                            <span className="spinner" />
                            Starting...
                          </>
                        ) : (
                          "Start Interview →"
                        )}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ═══════════════════════════════════════════
            Step 3: Adaptive Technical Chat
            ═══════════════════════════════════════════ */}
        {currentStep === 3 && (
          <div className="step-panel step-interview">
            <div className="step-header-bar">
              <button className="btn-back" onClick={() => goBackToStep(2)}>
                ← Back to Projects
              </button>
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                <span className="round-badge">
                  Round {interviewSession.round_count}
                </span>
                <span className="project-name-badge">
                  {selectedProject.name}
                </span>
                <button
                  className="btn btn-secondary"
                  style={{ fontSize: "0.8rem", padding: "0.35rem 0.75rem" }}
                  onClick={handleGenerateCaseStudy}
                  disabled={loading}
                >
                  Finish Early & Generate
                </button>
              </div>
            </div>

            <div className="interview-split-grid interview-fullheight">
              {/* Left Column: Chat Window */}
              <div className="chat-window">
                <div className="chat-header">
                  <div className="chat-bot-info">
                    <div className="bot-avatar">🤖</div>
                    <div>
                      <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "#f8fafc" }}>
                        <span className="bot-status-dot" /> AI Case Study Lead
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                        {interviewSession.status === "completed" ? "Interview Finished" : "Asking high-value missing details"}
                      </div>
                    </div>
                  </div>
                  {interviewSession.current_question && (
                    <span className="target-badge" style={{ margin: 0 }}>
                      Target: {interviewSession.current_question.target_area}
                    </span>
                  )}
                </div>

                {/* Chat Message Feed */}
                <div className="chat-feed">
                  {/* Past Exchanges */}
                  {(interviewSession.exchanges || [])
                    .filter((ex) => ex.answer !== null)
                    .map((ex) => (
                      <React.Fragment key={ex.id}>
                        <div className="msg-wrapper-ai">
                          <div className="bot-avatar">🤖</div>
                          <div className="bubble-ai">
                            <p style={{ margin: "0.25rem 0" }}>{ex.question}</p>
                            {ex.rationale && <p className="bubble-tip">Rationale: {ex.rationale}</p>}
                          </div>
                        </div>
                        <div className="msg-wrapper-user">
                          <div className="bubble-user">
                            {ex.answer}
                          </div>
                        </div>
                      </React.Fragment>
                    ))}

                  {/* Active Question Bubble */}
                  {interviewSession.current_question && (
                    <div className="msg-wrapper-ai">
                      <div className="bot-avatar">🤖</div>
                      <div className="bubble-ai" style={{ borderLeft: "3px solid #38bdf8" }}>
                        <p style={{ margin: "0.25rem 0", fontSize: "0.98rem", fontWeight: 500 }}>
                          {interviewSession.current_question.question}
                        </p>
                        {interviewSession.current_question.rationale && (
                          <p className="bubble-tip">
                            <em>{interviewSession.current_question.rationale}</em>
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Optimistic Pending User Response (visible immediately while AI processes) */}
                  {pendingAnswer && (
                    <div className="msg-wrapper-user">
                      <div className="bubble-user">
                        {pendingAnswer}
                      </div>
                    </div>
                  )}

                  {/* Loading indicator */}
                  {loading && (
                    <div className="msg-wrapper-ai">
                      <div className="bot-avatar">🤖</div>
                      <div className="chat-typing-indicator">
                        <span className="typing-dot" />
                        <span className="typing-dot" />
                        <span className="typing-dot" />
                        <span style={{ marginLeft: "0.35rem" }}>
                          {generatingCaseStudy
                            ? "Concluded interview. Generating case study..."
                            : "Extracting facts & evaluating criteria..."}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Interview Complete Banner */}
                  {interviewSession.status === "completed" && (
                    <div className="msg-wrapper-ai">
                      <div className="bot-avatar" style={{ background: "linear-gradient(135deg, #059669, #34d399)" }}>✓</div>
                      <div className="bubble-ai" style={{ borderLeft: "3px solid #34d399" }}>
                        <span className="target-badge" style={{ color: "#34d399", background: "rgba(16, 185, 129, 0.15)", borderColor: "rgba(16, 185, 129, 0.4)" }}>
                          Interview Complete
                        </span>
                        <p style={{ margin: "0.25rem 0" }}>
                          🎉 {interviewSession.stop_reason || "All essential technical dimensions have been captured."}
                        </p>
                        <button
                          className="btn"
                          style={{ marginTop: "0.75rem", width: "100%" }}
                          onClick={() => handleGenerateVariant("technical")}
                          disabled={loading}
                        >
                          {loading && generatingVariant === "technical" ? "Generating Technical Case Study..." : "🚀 Generate Technical Case Study Now"}
                        </button>
                        <button
                          className="btn btn-secondary"
                          style={{ marginTop: "0.45rem", width: "100%", borderColor: "rgba(56, 189, 248, 0.4)", color: "#38bdf8" }}
                          onClick={() => handleGenerateVariant("client_brochure")}
                          disabled={loading}
                        >
                          {loading && generatingVariant === "client_brochure" ? "Generating Client Brochure..." : "💼 Generate Client Brochure Now"}
                        </button>

                        {fulfilledCount < 8 && (
                          <button
                            className="btn"
                            style={{
                              marginTop: "0.5rem",
                              width: "100%",
                              background: "transparent",
                              border: "1px solid #38bdf8",
                              color: "#38bdf8",
                              fontWeight: 600
                            }}
                            onClick={handleContinueInterview}
                            disabled={loading}
                          >
                            💬 Continue Interview to Gather Remaining Topics ({8 - fulfilledCount} missing)
                          </button>
                        )}
                      </div>
                    </div>
                  )}

                  <div ref={chatEndRef} />
                </div>

                {/* Quick Actions (when question is pending) */}
                {interviewSession.current_question && !loading && (
                  <div className="chat-quick-actions">
                    <span style={{ fontSize: "0.74rem", color: "#64748b", marginRight: "0.2rem" }}>Quick replies:</span>
                    <button
                      type="button"
                      className="quick-chip"
                      onClick={() => handleSubmitAnswer("Skip this question for now.")}
                    >
                      ⏭️ Skip topic
                    </button>
                    <button
                      type="button"
                      className="quick-chip"
                      onClick={() => handleSubmitAnswer("No exact performance benchmarks recorded.")}
                    >
                      💡 No exact numbers
                    </button>
                    <button
                      type="button"
                      className="quick-chip"
                      onClick={() => handleSubmitAnswer("Standard engineering conventions; no major tradeoffs.")}
                    >
                      🤷 Not applicable
                    </button>
                    <button
                      type="button"
                      className="quick-chip"
                      style={{ borderColor: "rgba(239, 68, 68, 0.4)", color: "#fca5a5" }}
                      onClick={() => handleSubmitAnswer("I have nothing more to add.")}
                    >
                      🛑 I have nothing more to add
                    </button>
                  </div>
                )}

                {/* Chat Input Bar */}
                {interviewSession.current_question && (
                  <div className="chat-input-bar">
                    <textarea
                      className="chat-input-field"
                      rows={1}
                      value={answerInput}
                      onChange={(e) => setAnswerInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Type your answer... (Enter to send, Shift+Enter for newline)"
                      disabled={loading}
                    />
                    <button
                      className="chat-send-btn"
                      onClick={() => handleSubmitAnswer()}
                      disabled={!answerInput.trim() || loading}
                    >
                      {loading ? "..." : "Send 💬"}
                    </button>
                  </div>
                )}
              </div>

              {/* Right Column: Live Knowledge Ledger */}
              <div className="ledger-panel">
                <div className="ledger-header">
                  <div className="progress-header-row">
                    <strong style={{ color: "#f8fafc", fontSize: "0.92rem" }}>Live Knowledge Ledger</strong>
                    <span style={{ color: "#38bdf8", fontWeight: 700, fontSize: "0.82rem" }}>
                      {fulfilledCount}/8 Criteria ({progressPercent}%)
                    </span>
                  </div>
                  <div className="progress-bar-bg">
                    <div className="progress-bar-fill" style={{ width: `${progressPercent}%` }} />
                  </div>

                  {/* 8 Criteria Badges Grid */}
                  <div className="criteria-pill-grid">
                    {CRITERIA_AREAS.map((c) => {
                      const state = coverage[c.key] || "UNKNOWN";
                      const icon = state === "SUFFICIENT" ? "✓" : state === "PARTIAL" ? "◐" : "—";
                      return (
                        <div key={c.key} className={`criteria-card cov-${state}`} title={`${c.label}: ${state}`}>
                          <span>{c.label}</span>
                          <span style={{ fontWeight: 800 }}>{icon}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Scrollable Ledger Facts */}
                <div className="ledger-body">
                  {/* Captured from Conversation */}
                  <div>
                    <div className="ledger-section-title">
                      <span>💬 Captured in Chat</span>
                      <span className="ledger-count-pill">{conversationFacts.length} facts</span>
                    </div>
                    {conversationFacts.length > 0 ? (
                      conversationFacts.map((fact, idx) => (
                        <div key={`conv-${idx}`} className="fact-item source-conversation">
                          <span className="fact-tag">{fact.category || "detail"}</span>
                          {fact.fact}
                        </div>
                      ))
                    ) : (
                      <div className="ledger-empty-note">
                        Answers you provide in the chat will be dynamically analyzed and categorized here in real time.
                      </div>
                    )}
                  </div>

                  {/* Retrieved from Resume */}
                  <div>
                    <div className="ledger-section-title">
                      <span>📄 Retrieved from Resume</span>
                      <span className="ledger-count-pill">{resumeFacts.length} facts</span>
                    </div>
                    {resumeFacts.length > 0 ? (
                      resumeFacts.map((fact, idx) => (
                        <div key={`res-${idx}`} className="fact-item">
                          <span className="fact-tag">{fact.category || "resume"}</span>
                          {fact.fact}
                        </div>
                      ))
                    ) : (
                      <div className="ledger-empty-note">
                        Initial resume facts loaded from project extraction.
                      </div>
                    )}
                  </div>
                </div>

                {/* Footer */}
                <div className="ledger-footer">
                  <span style={{ fontSize: "0.78rem", color: "#94a3b8" }}>
                    Ready to generate anytime?
                  </span>
                  <button
                    className="btn"
                    style={{ padding: "0.45rem 0.85rem", fontSize: "0.82rem" }}
                    onClick={handleGenerateCaseStudy}
                    disabled={loading}
                  >
                    {loading ? "Generating..." : "Finish & Generate Now"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════
            Step 4: Final Technical Case Study & Client Brochure
            ═══════════════════════════════════════════ */}
        {currentStep === 4 && (
          <div className="step-panel step-casestudy" ref={caseStudyRef}>
            <div className="step-header-bar">
              <button className="btn-back" onClick={() => goBackToStep(3)}>
                ← Back to Interview
              </button>
              {caseStudy && (
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: "0.8rem", padding: "0.3rem 0.7rem" }}
                    onClick={() => handleGenerateVariant(activeVariant)}
                    disabled={loading || loadingVariant}
                    title="Regenerate this variant using the latest knowledge ledger"
                  >
                    🔄 Regenerate {activeVariant === "client_brochure" ? "Brochure" : "Case Study"}
                  </button>
                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: "0.8rem", padding: "0.3rem 0.7rem" }}
                    onClick={() => setShowRawMarkdown(!showRawMarkdown)}
                  >
                    {showRawMarkdown ? "👁️ Formatted View" : "📝 Raw Markdown"}
                  </button>
                </div>
              )}
            </div>

            {/* Audience Format Selector Tabs */}
            <div className="audience-toggle-container">
              <div className="audience-toggle-header">
                <div>
                  <span className="audience-eyebrow">AUDIENCE FORMAT SELECTOR</span>
                  <h3 className="audience-title">Choose Output Perspective</h3>
                </div>
                <div className="audience-sync-pill" title="Both variants are generated from the exact same verified knowledge ledger facts.">
                  <span className="sync-pulse-dot" />
                  <span>Synced to Knowledge Ledger ({allEvidence.length} facts)</span>
                </div>
              </div>

              <div className="audience-tabs">
                <button
                  type="button"
                  className={`audience-tab-btn ${activeVariant === "technical" ? "active" : ""}`}
                  onClick={() => handleSwitchAudience("technical")}
                  disabled={loading || loadingVariant}
                >
                  <div className="tab-icon-wrapper technical-icon">🛠️</div>
                  <div className="tab-text-wrapper">
                    <div className="tab-title-row">
                      <span className="tab-title">Technical Case Study</span>
                      {caseStudiesMap.technical ? (
                        <span className="tab-badge ready">✓ Ready</span>
                      ) : (
                        <span className="tab-badge pending">Available</span>
                      )}
                    </div>
                    <span className="tab-subtext">Deep architectural analysis & engineering tradeoffs</span>
                  </div>
                </button>

                <button
                  type="button"
                  className={`audience-tab-btn ${activeVariant === "client_brochure" ? "active" : ""}`}
                  onClick={() => handleSwitchAudience("client_brochure")}
                  disabled={loading || loadingVariant}
                >
                  <div className="tab-icon-wrapper brochure-icon">💼</div>
                  <div className="tab-text-wrapper">
                    <div className="tab-title-row">
                      <span className="tab-title">Client Brochure</span>
                      {caseStudiesMap.client_brochure ? (
                        <span className="tab-badge ready">✓ Ready</span>
                      ) : (
                        <span className="tab-badge action">⚡ Generate</span>
                      )}
                    </div>
                    <span className="tab-subtext">Executive summary, business ROI & client capabilities</span>
                  </div>
                </button>
              </div>
            </div>

            {/* Variant Loading State */}
            {loadingVariant && (
              <div className="variant-loading-card">
                <span className="spinner" />
                <span>Loading {activeVariant === "client_brochure" ? "Client Brochure" : "Technical Case Study"}...</span>
              </div>
            )}

            {/* Variant Generating State */}
            {!loadingVariant && loading && generatingVariant === activeVariant && (
              <div className="variant-loading-card">
                <span className="spinner" />
                <span>
                  Generating {activeVariant === "client_brochure" ? "Client Commercial Brochure" : "Technical Case Study"} from knowledge ledger...
                </span>
              </div>
            )}

            {/* If Current Variant is Available & Ready */}
            {!loadingVariant && !(loading && generatingVariant === activeVariant) && caseStudy && (
              <>
                {/* Variant Context Banner */}
                <div className={`variant-banner ${activeVariant === "client_brochure" ? "variant-brochure" : "variant-technical"}`}>
                  <span className="variant-banner-icon">
                    {activeVariant === "client_brochure" ? "💼" : "🛠️"}
                  </span>
                  <div>
                    <strong>
                      {activeVariant === "client_brochure" ? "Client-Facing Brochure" : "Deep Technical Case Study"}
                    </strong>
                    <span style={{ marginLeft: "0.5rem", opacity: 0.88 }}>
                      {activeVariant === "client_brochure"
                        ? "Curated for commercial clients, non-technical stakeholders, and executive leadership."
                        : "Curated for engineering hiring managers, software architects, and technical leads."}
                    </span>
                  </div>
                </div>

                {/* Export Toolbar */}
                <div className="export-bar">
                  <span style={{ fontSize: "0.85rem", color: "#94a3b8", fontWeight: 600, marginRight: "0.25rem" }}>
                    Export ({activeVariant === "client_brochure" ? "Brochure" : "Technical"}):
                  </span>
                  <a
                    href={getCaseStudyExportUrl(selectedProject.id, "pdf", activeVariant)}
                    className="btn-export primary-export"
                    target="_blank"
                    rel="noopener noreferrer"
                    download
                  >
                    📄 Download PDF {activeVariant === "client_brochure" ? "(2-Page Flyer)" : ""}
                  </a>
                  <a
                    href={getCaseStudyExportUrl(selectedProject.id, "docx", activeVariant)}
                    className="btn-export"
                    target="_blank"
                    rel="noopener noreferrer"
                    download
                  >
                    📝 Download Word (.docx)
                  </a>
                  <a
                    href={getCaseStudyExportUrl(selectedProject.id, "md", activeVariant)}
                    className="btn-export"
                    target="_blank"
                    rel="noopener noreferrer"
                    download
                  >
                    📋 Download Markdown (.md)
                  </a>
                  <button
                    className="btn-export"
                    onClick={() => window.print()}
                  >
                    🖨️ Print / Save as PDF
                  </button>
                </div>

                {showRawMarkdown ? (
                  <pre>{caseStudy.markdown_content}</pre>
                ) : (
                  <MarkdownRenderer content={caseStudy.markdown_content} />
                )}
              </>
            )}

            {/* If Current Variant is NOT yet generated */}
            {!loadingVariant && !(loading && generatingVariant === activeVariant) && !caseStudy && (
              <div className="brochure-empty-state">
                <div className="brochure-empty-icon">
                  {activeVariant === "client_brochure" ? "💼" : "🛠️"}
                </div>
                <h3 className="brochure-empty-title">
                  {activeVariant === "client_brochure"
                    ? "Generate Client-Facing Commercial Brochure"
                    : "Generate Deep Technical Case Study"}
                </h3>
                <p className="brochure-empty-desc">
                  {activeVariant === "client_brochure"
                    ? `Transform the verified engineering knowledge ledger for "${selectedProject?.name || "your project"}" into an executive-ready, 1-to-2 page commercial flyer designed for clients, investors, and business leaders.`
                    : `Generate the comprehensive technical blueprint for "${selectedProject?.name || "your project"}" covering system architecture, decisions, tradeoffs, and failure modes.`}
                </p>

                {activeVariant === "client_brochure" && (
                  <div className="brochure-highlights-grid">
                    <div className="highlight-pill">
                      <span className="hl-icon">📊</span>
                      <div>
                        <strong>Executive ROI Callout Boxes</strong>
                        <span>Highlights scale, efficiency, latency, and customer savings</span>
                      </div>
                    </div>
                    <div className="highlight-pill">
                      <span className="hl-icon">🤝</span>
                      <div>
                        <strong>Client Problem & Solution Narrative</strong>
                        <span>Explains business pain points and strategic capability delivery</span>
                      </div>
                    </div>
                    <div className="highlight-pill">
                      <span className="hl-icon">🖨️</span>
                      <div>
                        <strong>ReportLab 2-Page Flyer PDF</strong>
                        <span>Branded header, sidebar metrics, and commercial presentation</span>
                      </div>
                    </div>
                  </div>
                )}

                <button
                  type="button"
                  className="btn btn-lg brochure-generate-btn"
                  onClick={() => handleGenerateVariant(activeVariant)}
                  disabled={loading}
                >
                  {loading && generatingVariant === activeVariant ? (
                    <>
                      <span className="spinner" />
                      Generating...
                    </>
                  ) : activeVariant === "client_brochure" ? (
                    "⚡ Generate Client Brochure Now"
                  ) : (
                    "🚀 Generate Technical Case Study Now"
                  )}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
      </>
    )}

      {/* Modal: Add Unlisted Project */}
      {showAddProjectModal && (
        <div className="modal-backdrop" onClick={handleCloseAddProjectModal}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3 style={{ margin: "0 0 0.25rem 0", fontSize: "1.2rem", color: "#fff" }}>
                  Add Unlisted Technical Project
                </h3>
                <p style={{ margin: 0, fontSize: "0.82rem", color: "#94a3b8" }}>
                  Add a project not mentioned on your resume to conduct the interview and generate a technical case study.
                </p>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={handleCloseAddProjectModal}
                disabled={addingProject}
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddProjectSubmit} className="modal-form">
              <div className="modal-body">
                {addProjectError && (
                  <div style={{
                    padding: "0.65rem 0.85rem",
                    marginBottom: "1rem",
                    background: "rgba(239, 68, 68, 0.12)",
                    border: "1px solid rgba(239, 68, 68, 0.35)",
                    borderRadius: "6px",
                    color: "#fca5a5",
                    fontSize: "0.85rem"
                  }}>
                    ⚠️ {addProjectError}
                  </div>
                )}

                {/* Field 1: Project Name (Mandatory) */}
                <div className="form-group">
                  <label className="form-label">
                    <span>Project Name <span style={{ color: "#f87171" }}>*</span></span>
                    <span className="required-badge">Mandatory</span>
                  </label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Real-Time Telemetry Pipeline & Anomaly Detector"
                    value={addProjectForm.name}
                    onChange={(e) => setAddProjectForm({ ...addProjectForm, name: e.target.value })}
                    required
                    autoFocus
                    disabled={addingProject}
                  />
                </div>

                {/* Field 2: Description (Mandatory) */}
                <div className="form-group">
                  <label className="form-label">
                    <span>Description / Problem Statement <span style={{ color: "#f87171" }}>*</span></span>
                    <span className="required-badge">Mandatory</span>
                  </label>
                  <textarea
                    className="form-textarea"
                    rows={3}
                    placeholder="Briefly describe what this project does and the primary problem or requirement it addresses..."
                    value={addProjectForm.description}
                    onChange={(e) => setAddProjectForm({ ...addProjectForm, description: e.target.value })}
                    required
                    disabled={addingProject}
                  />
                  <div className="form-help">
                    Summarize what the system does and why it was built.
                  </div>
                </div>

                {/* Field 3: Technologies (Mandatory) */}
                <div className="form-group">
                  <label className="form-label">
                    <span>Technologies & Tech Stack <span style={{ color: "#f87171" }}>*</span></span>
                    <span className="required-badge">Mandatory</span>
                  </label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Python, FastAPI, React, Redis, PostgreSQL, Docker"
                    value={addProjectForm.technologies}
                    onChange={(e) => setAddProjectForm({ ...addProjectForm, technologies: e.target.value })}
                    required
                    disabled={addingProject}
                  />
                  <div className="form-help">
                    Enter tools, languages, or frameworks separated by commas.
                  </div>
                </div>

                {/* Field 4: Contributions (Optional) */}
                <div className="form-group">
                  <label className="form-label">
                    <span>Key Contributions & Architecture</span>
                    <span className="optional-badge">Optional</span>
                  </label>
                  <textarea
                    className="form-textarea"
                    rows={2}
                    placeholder="e.g. Engineered event stream ingestion worker; implemented fallback caching with Redis..."
                    value={addProjectForm.contributions}
                    onChange={(e) => setAddProjectForm({ ...addProjectForm, contributions: e.target.value })}
                    disabled={addingProject}
                  />
                  <div className="form-help">
                    Optional: Specific modules, algorithms, or architecture designs you built.
                  </div>
                </div>

                {/* Field 5: Outcomes & Metrics (Optional) */}
                <div className="form-group">
                  <label className="form-label">
                    <span>Measurable Outcomes & Metrics</span>
                    <span className="optional-badge">Optional</span>
                  </label>
                  <textarea
                    className="form-textarea"
                    rows={2}
                    placeholder="e.g. Processed 10k events/sec; reduced mean time to detect anomalies from 15m to 20s..."
                    value={addProjectForm.outcomes}
                    onChange={(e) => setAddProjectForm({ ...addProjectForm, outcomes: e.target.value })}
                    disabled={addingProject}
                  />
                  <div className="form-help">
                    Optional: Latency numbers, throughput, cost savings, or user adoption metrics.
                  </div>
                </div>

                {/* Field 6: Links (Optional) */}
                <div className="form-group">
                  <label className="form-label">
                    <span>Project Links / GitHub URL</span>
                    <span className="optional-badge">Optional</span>
                  </label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. https://github.com/example/pipeline"
                    value={addProjectForm.links}
                    onChange={(e) => setAddProjectForm({ ...addProjectForm, links: e.target.value })}
                    disabled={addingProject}
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleCloseAddProjectModal}
                  disabled={addingProject}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn"
                  disabled={addingProject}
                >
                  {addingProject ? (
                    <>
                      <span className="spinner" />
                      Saving Project...
                    </>
                  ) : (
                    "Save & Add Project"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ─── Responsive Authentication Modal ─── */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={handleCloseAuth}
        onAuthSuccess={handleAuthSuccess}
        initialMode={authModalMode}
      />
    </div>
  );
}
