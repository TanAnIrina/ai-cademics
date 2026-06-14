// Thin wrapper around the AI-cademics backend. All calls are same-origin
// ("/api/..."): in dev, Vite proxies to :8000; in prod, nginx does.

const TOKEN_KEY = "aicademics.token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request(path, { method = "GET", body, auth = false } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail = data && data.detail ? data.detail : res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export const api = {
  // auth
  login: (payload) => request("/api/auth/login", { method: "POST", body: payload }),
  me: () => request("/api/auth/me", { auth: true }),
  logout: () => request("/api/auth/logout", { method: "POST", auth: true }),

  // classrooms
  listClassrooms: () => request("/api/classrooms"),
  getClassroom: (id) => request(`/api/classrooms/${id}`),
  createClassroom: (name) => request("/api/classrooms", { method: "POST", body: { name }, auth: true }),
  joinClassroom: (id, config) =>
    request(`/api/classrooms/${id}/join`, {
      method: "POST",
      body: config ? { config } : {},
      auth: true,
    }),
  configureClassroom: (id, config) =>
    request(`/api/classrooms/${id}/configure`, { method: "POST", body: config, auth: true }),
  leaveClassroom: (id) => request(`/api/classrooms/${id}/leave`, { method: "POST", auth: true }),
  liveView: (id) => request(`/api/classrooms/${id}/live`),
  estimate: (sprint, brk, max) =>
    request(`/api/classrooms/estimate?sprint_minutes=${sprint}&break_minutes=${brk}&max_sprints=${max}`),

  // chat
  getChat: (id, afterId = 0) => request(`/api/classrooms/${id}/chat?after_id=${afterId}`),
  postChat: (id, nickname, content) =>
    request(`/api/classrooms/${id}/chat`, { method: "POST", body: { nickname, content } }),

  // history
  listHistory: () => request("/api/history"),
  getArchive: (id) => request(`/api/history/${id}`),
};
