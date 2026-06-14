import { useCallback, useEffect, useRef, useState } from "react";

// Poll an async function on an interval. Returns the latest data, a loading
// flag for the first fetch, any error, and a manual refresh(). Polling pauses
// automatically when the browser tab is hidden.
export function usePolling(fn, intervalMs = 2000, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const savedFn = useRef(fn);
  savedFn.current = fn;

  const refresh = useCallback(async () => {
    try {
      const result = await savedFn.current();
      setData(result);
      setError(null);
    } catch (e) {
      setError(e.message || "Request failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let timer = null;
    let active = true;

    const tick = async () => {
      if (document.hidden) return;
      if (active) await refresh();
    };

    refresh();
    timer = setInterval(tick, intervalMs);
    const onVis = () => {
      if (!document.hidden) refresh();
    };
    document.addEventListener("visibilitychange", onVis);

    return () => {
      active = false;
      if (timer) clearInterval(timer);
      document.removeEventListener("visibilitychange", onVis);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, loading, error, refresh };
}
