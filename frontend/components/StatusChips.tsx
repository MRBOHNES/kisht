"use client";

import { useContactHoursOpen, useOnline } from "@/lib/hooks";
import { useLang } from "@/lib/i18n";

function Chip({ tone, children }: { tone: "green" | "red" | "amber"; children: React.ReactNode }) {
  const tones = { green: "bg-green-bg text-green", red: "bg-red-bg text-red", amber: "bg-amber-bg text-amber" };
  return <span className={`rounded-full px-3 py-1 text-xs font-medium ${tones[tone]}`}>{children}</span>;
}

// Display only; the server enforces the contact window.
export function StatusChips() {
  const { t } = useLang();
  const open = useContactHoursOpen();
  const online = useOnline();
  return (
    <div className="flex flex-wrap gap-2">
      {open !== null && <Chip tone={open ? "green" : "red"}>{open ? t("hoursOpen") : t("hoursClosed")}</Chip>}
      <Chip tone={online ? "green" : "amber"}>{online ? t("online") : t("offline")}</Chip>
    </div>
  );
}
