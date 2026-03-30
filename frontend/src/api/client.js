import axios from "axios";

// When served from FastAPI (same domain), use relative URLs.
// When running dev server separately, use VITE_API_BASE_URL.
const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

const api = axios.create({ baseURL: BASE });

// Inject API key + access token on every request
api.interceptors.request.use((config) => {
  const key = localStorage.getItem("rpf_api_key");
  if (key) config.headers["X-API-Key"] = key;
  const token = localStorage.getItem("rpf_access_token");
  if (token) config.headers["X-Access-Token"] = token;
  return config;
});

// On 401 — clear tokens and reload to show setup screen
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("rpf_api_key");
    }
    return Promise.reject(err);
  }
);

export async function searchPapers(payload) {
  const { data } = await api.post("/search", payload);
  return data; // Returns { task_id }
}

export async function getSearchStatus(taskId) {
  const { data } = await api.get(`/search/status/${taskId}`);
  return data;
}

export async function createApiKey(name) {
  const { data } = await api.post("/auth/keys", { name });
  return data;
}

export async function listApiKeys() {
  const { data } = await api.get("/auth/keys");
  return data;
}

export { api, BASE };
