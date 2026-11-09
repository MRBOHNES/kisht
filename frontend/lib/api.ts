"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export class ApiError extends Error {
  constructor(public status: number, public detail: unknown) {
    super(`API error ${status}`);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...init.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, body.detail);
  }
  return response.json();
}

type Loaded<T> = { data?: T; error?: unknown; loading: boolean; savedAt?: string };

const CACHE_PREFIX = "kisht.cache.";

function readCache<T>(key: string): { data: T; savedAt: string } | null {
  try {
    return JSON.parse(window.localStorage.getItem(CACHE_PREFIX + key) ?? "null");
  } catch {
    return null;
  }
}

/** Borrower data cached for offline reading is removed when the officer signs out. */
export function clearReadCache() {
  Object.keys(window.localStorage)
    .filter((key) => key.startsWith(CACHE_PREFIX))
    .forEach((key) => window.localStorage.removeItem(key));
}

/**
 * GETs a path on mount; sends the user to the login page if the session has ended.
 * With `cache`, the last good response is kept on the phone and shown when the network is down.
 */
export function useApi<T>(path: string, cache = false) {
  const router = useRouter();
  const [state, setState] = useState<Loaded<T>>({ loading: true });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let current = true;
    api<T>(path).then(
      (data) => {
        if (!current) return;
        if (cache) window.localStorage.setItem(CACHE_PREFIX + path, JSON.stringify({ data, savedAt: new Date().toISOString() }));
        setState({ data, loading: false });
      },
      (error) => {
        if (!current) return;
        if (error instanceof ApiError && error.status === 401) {
          router.replace("/login");
          return;
        }
        const saved = cache && !(error instanceof ApiError) ? readCache<T>(path) : null;
        setState(saved ? { data: saved.data, savedAt: saved.savedAt, loading: false } : { error, loading: false });
      },
    );
    return () => {
      current = false;
    };
  }, [path, router, attempt, cache]);

  function reload() {
    setState({ loading: true });
    setAttempt((n) => n + 1);
  }

  return { ...state, reload };
}

export function cachedValue<T>(path: string): T | null {
  return readCache<T>(path)?.data ?? null;
}
