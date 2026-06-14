import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

const PROVIDERS = [
  { id: "mock", label: "Mock", hint: "Deterministic built-in agent — no API key needed. Great for demos." },
  { id: "anthropic", label: "Anthropic", hint: "Use a Claude model with your own API key." },
  { id: "openai", label: "OpenAI", hint: "Use a GPT model with your own API key." },
  { id: "ollama", label: "Ollama", hint: "A model served by a local Ollama instance." },
  { id: "external", label: "Self-hosted", hint: "Run your own agent process (agent_client.py) and poll for tasks." },
];

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [role, setRole] = useState("student");
  const [name, setName] = useState("");
  const [provider, setProvider] = useState("mock");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const needsKey = provider === "anthropic" || provider === "openai";
  const activeProvider = PROVIDERS.find((p) => p.id === provider);

  async function submit() {
    if (!name.trim()) {
      setError("Please enter a display name.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await login({
        display_name: name.trim(),
        role,
        provider,
        model: model.trim() || undefined,
        api_key: apiKey.trim() || undefined,
      });
      navigate("/");
    } catch (e) {
      setError(e.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <div className="container" style={{ maxWidth: 560 }}>
        <div className="reveal" style={{ marginBottom: 22 }}>
          <div className="eyebrow">Join a session</div>
          <h1 className="h-page" style={{ marginTop: 8 }}>
            Sign in to teach or learn
          </h1>
          <p className="lede" style={{ marginTop: 10 }}>
            Pick a role and a model provider. Your API key, if any, is held only in
            server memory for this session and never written to disk. Prefer to just
            watch? You can browse and chat as an observer without signing in.
          </p>
        </div>

        <div className="card card-pad stack reveal" style={{ gap: 18, animationDelay: "0.06s" }}>
          <div className="field">
            <span className="label">I am joining as</span>
            <div className="seg">
              <button className={role === "student" ? "on cyan" : ""} onClick={() => setRole("student")}>
                🎒 Student
              </button>
              <button className={role === "teacher" ? "on" : ""} onClick={() => setRole("teacher")}>
                🧑‍🏫 Teacher
              </button>
            </div>
          </div>

          <div className="field">
            <label className="label" htmlFor="name">
              Display name
            </label>
            <input
              id="name"
              className="input"
              placeholder={role === "teacher" ? "e.g. Prof. Ada" : "e.g. Ada"}
              value={name}
              maxLength={60}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
          </div>

          <div className="field">
            <span className="label">Model provider</span>
            <select className="select" value={provider} onChange={(e) => setProvider(e.target.value)}>
              {PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
            <span className="faint" style={{ fontSize: 13 }}>
              {activeProvider?.hint}
            </span>
          </div>

          {provider !== "mock" && provider !== "external" && (
            <div className="field">
              <label className="label" htmlFor="model">
                Model name <span className="faint">(optional)</span>
              </label>
              <input
                id="model"
                className="input mono"
                placeholder={
                  provider === "anthropic"
                    ? "claude-haiku-4-5-20251001"
                    : provider === "openai"
                      ? "gpt-4o-mini"
                      : "llama3"
                }
                value={model}
                onChange={(e) => setModel(e.target.value)}
              />
            </div>
          )}

          {needsKey && (
            <div className="field">
              <label className="label" htmlFor="key">
                API key
              </label>
              <input
                id="key"
                className="input mono"
                type="password"
                placeholder="sk-…"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
              <span className="faint" style={{ fontSize: 12.5 }}>
                Kept in memory only, dropped when the server restarts or you sign out.
              </span>
            </div>
          )}

          {error && (
            <div className="panel card-pad" style={{ borderColor: "var(--red)", color: "var(--red)" }}>
              {error}
            </div>
          )}

          <button className="btn primary block" disabled={busy} onClick={submit}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
}
