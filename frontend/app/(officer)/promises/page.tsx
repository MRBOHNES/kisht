"use client";

import Link from "next/link";
import { useState } from "react";

import { BottomTabs } from "@/components/BottomTabs";
import { LangToggle } from "@/components/LangToggle";
import { PendingBanner } from "@/components/PendingBanner";
import { Sparkline } from "@/components/Sparkline";
import { EmptyState, ErrorState, Skeleton } from "@/components/States";
import { useApi } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { businessLabel, dayAndMonth, formatRupees, type StringKey } from "@/lib/strings";

type PromiseCard = {
  id: number;
  loan_id: string;
  business_name: string;
  business_type: string;
  amount: number;
  promised_date: string;
  status: "open" | "kept" | "broken";
};
type PromisesData = {
  kept_rate: number | null;
  kept_rate_weeks: (number | null)[];
  today: PromiseCard[];
  not_kept: PromiseCard[];
  upcoming: PromiseCard[];
};
type Tab = "today" | "not_kept" | "upcoming";

const TABS: { tab: Tab; label: StringKey; empty: StringKey; status: StringKey; tone: string }[] = [
  { tab: "today", label: "tabToday", empty: "emptyPromisesToday", status: "statusDueToday", tone: "bg-amber-bg text-amber" },
  { tab: "not_kept", label: "tabNotKept", empty: "emptyNotKept", status: "statusNotKept", tone: "bg-red-bg text-red" },
  { tab: "upcoming", label: "tabUpcoming", empty: "emptyUpcoming", status: "statusUpcoming", tone: "bg-green-bg text-green" },
];

export default function PromisesPage() {
  const { t } = useLang();
  const { data, error, loading, reload } = useApi<PromisesData>("/officer/promises", true);
  const [tab, setTab] = useState<Tab>("today");
  const current = TABS.find((x) => x.tab === tab)!;

  return (
    <main className="pt-4 pb-20">
      <header className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">{t("promisesTitle")}</h1>
        <LangToggle />
      </header>
      <PendingBanner />

      {loading && (
        <div className="mt-4 flex flex-col gap-3">
          <Skeleton className="h-20" />
          <Skeleton className="h-12" />
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
      )}
      {error !== undefined && !loading && (
        <div className="mt-4">
          <ErrorState message={t("errLoad")} onRetry={reload} />
        </div>
      )}
      {data && !loading && (
        <>
          <section className="card mt-4 flex items-center justify-between p-4">
            <div>
              <p className="text-xs text-muted">{t("keptRate")}</p>
              {data.kept_rate === null ? (
                <p className="mt-1 text-sm text-muted">{t("keptRateNone")}</p>
              ) : (
                <p className="mt-1 text-2xl font-semibold">{Math.round(data.kept_rate * 100)}%</p>
              )}
            </div>
            <Sparkline values={data.kept_rate_weeks} />
          </section>

          <div role="tablist" className="mt-4 grid grid-cols-3 gap-1 rounded-xl bg-line p-1">
            {TABS.map((x) => (
              <button
                key={x.tab}
                type="button"
                role="tab"
                aria-selected={tab === x.tab}
                onClick={() => setTab(x.tab)}
                className={`min-h-12 rounded-lg text-sm font-medium ${tab === x.tab ? "bg-card text-ink" : "text-muted"}`}
              >
                {t(x.label)} ({data[x.tab].length})
              </button>
            ))}
          </div>

          <div className="mt-3">
            {data[tab].length === 0 ? (
              <EmptyState message={t(current.empty)} />
            ) : (
              <ul className="flex flex-col gap-2">
                {data[tab].map((p) => (
                  <li key={p.id}>
                    <PromiseRow promise={p} status={t(current.status)} tone={current.tone} />
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
      <BottomTabs />
    </main>
  );
}

function PromiseRow({ promise, status, tone }: { promise: PromiseCard; status: string; tone: string }) {
  const { lang } = useLang();
  const { day, month } = dayAndMonth(promise.promised_date, lang);
  return (
    <Link href={`/loan/${encodeURIComponent(promise.loan_id)}`} className="card flex items-center gap-3 p-3 active:bg-bg">
      <div className="flex h-14 w-14 shrink-0 flex-col items-center justify-center rounded-xl bg-bg">
        <span className="text-lg leading-none font-semibold">{day}</span>
        <span className="text-xs text-muted">{month}</span>
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{businessLabel(promise.business_name, promise.business_type, lang)}</p>
        <p className="text-xs text-muted">{promise.loan_id}</p>
      </div>
      <div className="text-right">
        <p className="font-semibold">{formatRupees(promise.amount)}</p>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${tone}`}>{status}</span>
      </div>
    </Link>
  );
}
