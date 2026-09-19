"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type State<T> = { data: T | null; loading: boolean; error: string | null };

/**
 * Fetches an async producer on mount (and when `key` changes).
 * `key` must be a stable primitive so effects re-run predictably.
 */
export function useFetch<T>(fetcher: () => Promise<T>, key: string): State<T> & { retry: () => void } {
  const [state, setState] = useState<State<T>>({ data: null, loading: true, error: null });
  const [attempt, setAttempt] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    let cancelled = false;
    setState((current) => ({ ...current, loading: true, error: null }));
    fetcherRef
      .current()
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({
            data: null,
            loading: false,
            error: error instanceof Error ? error.message : "Request failed",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [key, attempt]);

  const retry = useCallback(() => setAttempt((current) => current + 1), []);
  return { ...state, retry };
}
