const API_BASE = "http://localhost:8000/api";

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
