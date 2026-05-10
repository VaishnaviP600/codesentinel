import axios from "axios";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const authAPI = {
  login: (username, password) => {
    const form = new FormData();
    form.append("username", username);
    form.append("password", password);
    return api.post("/api/auth/login", form);
  },
  register: (username, email, password) =>
    api.post("/api/auth/register", { username, email, password }),
};

export const scansAPI = {
  list: (page = 1) => api.get(`/api/scans?page=${page}`),
  getFindings: (scanId, params = {}) =>
    api.get(`/api/scans/${scanId}/findings`, { params }),
  manualScan: (repo_url, branch) =>
    api.post("/api/scan/manual", { repo_url, branch }),
  getStats: () => api.get("/api/stats"),
};

export const createWebSocket = (scanId) => {
  const wsUrl = process.env.REACT_APP_WS_URL || "ws://localhost:8000";
  return new WebSocket(`${wsUrl}/ws/${scanId}`);
};

export default api;
