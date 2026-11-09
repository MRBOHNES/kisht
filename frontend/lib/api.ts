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

type Loaded<T> = { data?: T; error?: unknown; loading: boolean };

/** GETs a path on mount; sends the user to the login page if the session has ended. */
export function useApi<T>(path: string) {
  const router = useRouter();
  const [state, setState] = useState<Loaded<T>>({ loading: true });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let current = true;
    api<T>(path).then(
      (data) => {
        if (current) setState({ data, loading: false });
      },
      (error) => {
        if (!current) return;
        if (error instanceof ApiError && error.status === 401) router.replace("/login");
        else setState({ error, loading: false });
      },
    );
    return () => {
      current = false;
    };
  }, [path, router, attempt]);

  function reload() {
    setState({ loading: true });
    setAttempt((n) => n + 1);
  }

  return { ...state, reload };
}
