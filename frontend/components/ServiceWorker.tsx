"use client";

import { useEffect } from "react";

export function ServiceWorker() {
  useEffect(() => {
    // dev rebuilds would fight with cached pages
    if (process.env.NODE_ENV === "production" && "serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => undefined);
    }
  }, []);
  return null;
}
