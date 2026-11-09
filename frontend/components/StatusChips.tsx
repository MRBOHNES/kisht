"use client";

import { useSyncExternalStore } from "react";

import { useLang } from "@/lib/i18n";

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

function Chip({ tone, children }: { tone: "green" | "red" | "amber"; children: React.ReactNode }) {
  const tones = { green: "bg-green-bg text-green", red: "bg-red-bg text-red", amber: "bg-amber-bg text-amber" };
  return <span className={`rounded-full px-3 py-1 text-xs font-medium ${tones[tone]}`}>{children}</span>;
}

// Display only; the server enforces the contact window.
export function StatusChips() {
  const { t } = useLang();
  const open = useSyncExternalStore(subscribeMinute, contactHoursOpen, () => null);
  const online = useSyncExternalStore(subscribeOnline, () => navigator.onLine, () => true);
  return (
    <div className="flex flex-wrap gap-2">
      {open !== null && <Chip tone={open ? "green" : "red"}>{open ? t("hoursOpen") : t("hoursClosed")}</Chip>}
      <Chip tone={online ? "green" : "amber"}>{online ? t("online") : t("offline")}</Chip>
    </div>
  );
}
