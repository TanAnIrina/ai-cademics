// Schimbi DOAR aici dacă rulezi backendul pe alt IP/port.
export const API_BASE = "http://localhost:8000";

async function j(url, opts = {}) {
  const r = await fetch(`${API_BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    throw new Error(`${r.status} ${url}: ${text || r.statusText}`);
  }
  return r.json();
}

// ── GET ────────────────────────────────────────────────
export const getRoot         = ()         => j("/");
export const getLeaderboard  = ()         => j("/api/leaderboard");
export const getStudents     = ()         => j("/api/students");
export const getStudent      = (name)     => j(`/api/students/${name}`);
export const getStudentBadges     = (name) => j(`/api/students/${name}/badges`);
export const getStudentProgression= (name) => j(`/api/students/${name}/progression`);
export const getStudentEmotionHistory = (name, limit = 100) =>
  j(`/api/students/${name}/emotions/history?limit=${limit}`);
export const getAchievements = ()         => j("/api/achievements");
export const getStats        = ()         => j("/api/stats");
export const getSprints      = (limit=20) => j(`/api/sprints?limit=${limit}`);
export const getSprint       = (id)       => j(`/api/sprints/${id}`);
export const getEmotions     = ()         => j("/api/emotions");

// NEW: live progress
export const getLive         = ()         => j("/api/live");

// ── POST ───────────────────────────────────────────────
const post = (url, body) => j(url, { method: "POST", body: JSON.stringify(body) });

export const runSprint = ({ subject, answer_timeout=90, sanction_threshold=4, reward_threshold=8 }) =>
  post("/api/sprint/run", { subject, answer_timeout, sanction_threshold, reward_threshold });

export const runBreak = ({ rounds=5, timeout=60 }) =>
  post("/api/break/run", { rounds, timeout });

export const runFullSession = (cfg) => post("/api/session/run", cfg);

export const updateEmotion = (student_name, frustration_delta=0, happiness_delta=0) =>
  post("/api/emotions/update", { student_name, frustration_delta, happiness_delta });

export const resetEmotions = () => post("/api/emotions/reset", {});
export const resetDatabase = () => post("/api/db/reset", {});
