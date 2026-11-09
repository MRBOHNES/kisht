"use client";

import { useSyncExternalStore } from "react";

function contactHoursOpen(): boolean {
  const hour = Number(
    new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata", hour: "numeric", hourCycle: "h23" }),
  );
  return hour >= 8 && hour < 19;
}

function subscribeMinute(callback: () => void) {
  const id = window.setInterval(callback, 60_000);
  return () => window.clearInterval(id);
}

function subscribeOnline(callback: () => void) {
  window.addEventListener("online", callback);
  window.addEventListener("offline", callback);
  return () => {
    window.removeEventListener("online", callback);
    window.removeEventListener("offline", callback);
  };
}

/** Whether it is 08:00-19:00 in India; null until known in the browser. Display only: the server decides. */
export function useContactHoursOpen(): boolean | null {
  return useSyncExternalStore(subscribeMinute, contactHoursOpen, () => null);
}

export function useOnline(): boolean {
  return useSyncExternalStore(subscribeOnline, () => navigator.onLine, () => true);
}
