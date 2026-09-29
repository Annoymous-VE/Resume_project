const DEPLOYED_BACKEND_URL = "https://resume-project-osw9.onrender.com";
const LOCAL_BACKEND_URL = "http://localhost:8000";

export function getApiBase() {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && typeof envUrl === "string" && envUrl.trim()) {
    const clean = envUrl.trim().replace(/\/+$/, "");
    return clean.endsWith("/api") ? clean : `${clean}/api`;
  }

  // If running in browser on localhost / 127.0.0.1, connect to local backend
  if (
    typeof window !== "undefined" &&
    (window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1")
  ) {
    return `${LOCAL_BACKEND_URL}/api`;
  }

  // Deployed production environment (Vercel, etc.)
  return `${DEPLOYED_BACKEND_URL}/api`;
}

export const API_BASE = getApiBase();

export async function uploadResume(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/resumes`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to upload resume.");
  }
  return res.json();
}

export async function fetchProjects() {
  const res = await fetch(`${API_BASE}/projects`);
  if (!res.ok) throw new Error("Failed to fetch projects.");
  return res.json();
}

export async function createProject(projectData) {
  const res = await fetch(`${API_BASE}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(projectData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to create project.");
  }
  return res.json();
}

export async function fetchProjectKnowledge(projectId) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/knowledge`);
  if (!res.ok) throw new Error("Failed to fetch project knowledge.");
  return res.json();
}

export async function startInterview(projectId) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/interview/start`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to start interview.");
  return res.json();
}

export async function submitAnswer(projectId, exchangeId, answer) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/interview/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ exchange_id: exchangeId, answer }),
  });
  if (!res.ok) throw new Error("Failed to submit answer.");
  return res.json();
}

export async function continueInterview(projectId) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/interview/continue`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to continue interview.");
  return res.json();
}

export async function fetchInterviewStatus(projectId) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/interview/status`);
  if (!res.ok) throw new Error("Failed to fetch interview status.");
  return res.json();
}

export async function generateCaseStudy(projectId) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/case-study/generate`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to generate case study.");
  return res.json();
}

export async function fetchCaseStudy(projectId) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/case-study`);
  if (!res.ok) throw new Error("Case study not found.");
  return res.json();
}

export function getCaseStudyExportUrl(projectId, format) {
  return `${API_BASE}/projects/${projectId}/case-study/export/${format}`;
}

