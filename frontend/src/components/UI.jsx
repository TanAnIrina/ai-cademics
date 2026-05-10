export function Loading({ label = "Loading…" }) {
  return <div className="loading">{label}</div>
}

export function ErrorBox({ error }) {
  if (!error) return null
  return <div className="error">⚠ {String(error.message || error)}</div>
}

export function useFetch() {
  // Lightweight helper not used directly; pages use their own useEffect calls.
  return null
}
