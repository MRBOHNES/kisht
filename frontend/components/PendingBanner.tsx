"use client";

import Link from "next/link";

import { useLang } from "@/lib/i18n";
import { useOutbox } from "@/lib/outbox";

export function PendingBanner() {
  const { t } = useLang();
  const pending = useOutbox().filter((item) => item.state === "pending").length;
  if (pending === 0) return null;
  return (
    <Link href="/sync" className="mt-2 flex min-h-12 items-center rounded-xl bg-amber-bg px-3 text-sm font-medium text-amber">
      {t("pendingBanner", { n: pending })}
    </Link>
  );
}
