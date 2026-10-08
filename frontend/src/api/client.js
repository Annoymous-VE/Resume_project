const DEPLOYED_BACKEND_URL = "https://resume-project-osw9.onrender.com";
const LOCAL_BACKEND_URL = "http://localhost:8000";

const TOKEN_KEY = "rcs_auth_token";
const REFRESH_TOKEN_KEY = "rcs_refresh_token";
const USER_KEY = "rcs_auth_user";

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

/* ─── Auth Session Storage Helpers ─── */
// Clean any legacy persistent credentials so fresh visits always land on the standard page
if (typeof window !== "undefined") {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  } catch {}
}

export function getStoredToken() {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(TOKEN_KEY);
}

export function getStoredRefreshToken() {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getStoredUser() {
  if (typeof window === "undefined") return null;
  try {
    const u = sessionStorage.getItem(USER_KEY);
    return u ? JSON.parse(u) : null;
  } catch {
    return null;
  }
}

export function setAuthSession(token, refreshToken, user) {
  if (typeof window === "undefined") return;
  if (token) sessionStorage.setItem(TOKEN_KEY, token);
  if (refreshToken) sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  if (user) sessionStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuthSession() {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  } catch {}
}

export function getAuthHeaders() {
  const token = getStoredToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/* ─── Auth API Calls ─── */
export async function registerUser({ email, password, full_name }) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Registration failed. Please check your credentials.");
  }
  const data = await res.json();
  setAuthSession(data.access_token, data.refresh_token, data.user);
  return data;
}

export async function loginUser({ email, password }) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Invalid email or password.");
  }
  const data = await res.json();
  setAuthSession(data.access_token, data.refresh_token, data.user);
  return data;
}

export async function fetchCurrentUser() {
  const headers = getAuthHeaders();
  if (!headers.Authorization) return null;

  const res = await fetch(`${API_BASE}/auth/me`, { headers });
  if (!res.ok) {
    clearAuthSession();
    return null;
  }
  const user = await res.json();
  if (typeof window !== "undefined") {
    sessionStorage.setItem(USER_KEY, JSON.stringify(user));
  }
  return user;
}

export function logoutUser() {
  clearAuthSession();
}

/* ─── Resume & Project API Calls (with Auth headers) ─── */
export async function uploadResume(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/resumes`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to upload resume.");
  }
  return res.json();
}

export async function fetchUserResumes() {
  const res = await fetch(`${API_BASE}/resumes`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchProjects() {
  const res = await fetch(`${API_BASE}/projects`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to fetch projects.");
  return res.json();
}

export async function createProject(projectData) {
  const res = await fetch(`${API_BASE}/projects`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(projectData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to create project.");
  }
  return res.json();
}

export async function fetchProjectKnowledge(projectId) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/knowledge`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to fetch project knowledge.");
  return res.json();
}

export async function startInterview(projectId) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/interview/start`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to start interview.");
  return res.json();
}

export async function submitAnswer(projectId, exchangeId, answer) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/interview/answer`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ exchange_id: exchangeId, answer }),
  });
  if (!res.ok) throw new Error("Failed to submit answer.");
  return res.json();
}

export async function continueInterview(projectId) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/interview/continue`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to continue interview.");
  return res.json();
}

export async function fetchInterviewStatus(projectId) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/interview/status`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to fetch interview status.");
  return res.json();
}

export async function generateCaseStudy(projectId, variantType = "technical") {
  const url = `${API_BASE}/projects/${projectId}/case-study/generate?variant_type=${encodeURIComponent(variantType)}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to generate case study.");
  }
  return res.json();
}

export async function fetchCaseStudy(projectId, variantType = "technical") {
  const url = `${API_BASE}/projects/${projectId}/case-study?variant_type=${encodeURIComponent(variantType)}`;
  const res = await fetch(url, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Case study not found.");
  }
  return res.json();
}

export async function fetchAllCaseStudies(projectId) {
  const url = `${API_BASE}/projects/${projectId}/case-study/all`;
  const res = await fetch(url, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) return [];
  return res.json();
}

export function getCaseStudyExportUrl(projectId, format, variantType = "technical") {
  const token = getStoredToken();
  const base = `${API_BASE}/projects/${projectId}/case-study/export/${format}?variant_type=${encodeURIComponent(variantType)}`;
  return token ? `${base}&token=${encodeURIComponent(token)}` : base;
}

export async function fetchDashboard() {
  const res = await fetch(`${API_BASE}/dashboard`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to load dashboard data.");
  return res.json();
}

export async function deleteProject(projectId) {
  const res = await fetch(`${API_BASE}/dashboard/projects/${projectId}`, {
    method: "DELETE",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to delete project.");
  return res.json();
}

export async function deleteResume(resumeId) {
  const res = await fetch(`${API_BASE}/dashboard/resumes/${resumeId}`, {
    method: "DELETE",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to delete resume.");
  return res.json();
}

export async function reExtractResume(resumeId) {
  const res = await fetch(`${API_BASE}/resumes/${resumeId}/re-extract`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to re-extract projects.");
  }
  return res.json();
}
