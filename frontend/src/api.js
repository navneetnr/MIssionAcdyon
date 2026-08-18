// Base URL comes from the environment so production builds never hardcode
// localhost. Set VITE_API_URL in .env (see .env.example) or in your hosting
// provider's dashboard when deploying.
const API_URL = import.meta.env.VITE_API_URL || "https://missionacdyon.onrender.com";

async function request(path, options) {
  const res = await fetch(`${API_URL}${path}`, options);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // response wasn't JSON, fall back to statusText
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export function fetchJobs({ search, category, jobType, location, limit = 20, offset = 0 } = {}) {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (category) params.set("category", category);
  if (jobType) params.set("job_type", jobType);
  if (location) params.set("location", location);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return request(`/api/jobs?${params.toString()}`);
}

export function fetchHealth() {
  return request("/health");
}

export function triggerIngest() {
  return request("/api/ingest", { method: "POST" });
}
