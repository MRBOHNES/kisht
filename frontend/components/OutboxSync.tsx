"use client";

import { useEffect } from "react";

import { syncOutbox } from "@/lib/outbox";

const RETRY_MS = 60_000;

/** Sends saved outcomes when the phone comes back online, and retries every minute while any are waiting. */
export function OutboxSync() {
  useEffect(() => {
    const trySync = () => {
      if (navigator.onLine) syncOutbox().catch(() => undefined);
    };
    trySync();
    window.addEventListener("online", trySync);
    const timer = window.setInterval(trySync, RETRY_MS);
    return () => {
      window.removeEventListener("online", trySync);
      window.clearInterval(timer);
    };
  }, []);
  return null;
}
