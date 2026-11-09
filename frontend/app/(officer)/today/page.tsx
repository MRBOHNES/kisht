"use client";

import { useRouter } from "next/navigation";

import { BottomTabs } from "@/components/BottomTabs";
import { LangToggle } from "@/components/LangToggle";
import { LoanCard, type LoanCardData } from "@/components/LoanCard";
import { EmptyState, ErrorState, Skeleton } from "@/components/States";
import { StatusChips } from "@/components/StatusChips";
import { api, useApi } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { formatRupees } from "@/lib/strings";

type TodayData = {
  officer_name: string;
  kpis: { list_count: number; promises_today: number; collected_today: number };
  loans: LoanCardData[];
};

export default function TodayPage() {
  const { t } = useLang();
  const router = useRouter();
  const { data, error, loading, reload } = useApi<TodayData>("/officer/today");

  async function signOut() {
    await api("/auth/logout", { method: "POST" }).catch(() => undefined);
    router.replace("/login");
  }

  return (
    <main className="pt-4 pb-20">
      <header className="flex items-center justify-between gap-2">
        <h1 className="text-lg font-semibold">
          {data ? t("greeting", { name: data.officer_name.split(" ")[0] }) : " "}
        </h1>
        <div className="flex gap-2">
          <LangToggle />
          <button type="button" onClick={signOut} className="min-h-12 px-2 text-sm text-muted">
            {t("signOut")}
          </button>
        </div>
      </header>
      <div className="mt-2">
        <StatusChips />
      </div>

      {loading && <TodaySkeleton />}
      {error !== undefined && !loading && (
        <div className="mt-6">
          <ErrorState message={t("errLoad")} onRetry={reload} />
        </div>
      )}
      {data && !loading && (
        <>
          <section className="mt-4 grid grid-cols-3 gap-2">
            <Kpi label={t("kpiList")} value={String(data.kpis.list_count)} />
            <Kpi label={t("kpiPromises")} value={String(data.kpis.promises_today)} />
            <Kpi label={t("kpiCollected")} value={formatRupees(data.kpis.collected_today)} />
          </section>
          <h2 className="mt-6 mb-2 font-semibold">{t("listTitle")}</h2>
          {data.loans.length === 0 ? (
            <EmptyState message={t("emptyList")} />
          ) : (
            <ol className="flex flex-col gap-3">
              {data.loans.map((loan) => (
                <li key={loan.loan_id}>
                  <LoanCard loan={loan} />
                </li>
              ))}
            </ol>
          )}
        </>
      )}
      <BottomTabs />
    </main>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="card p-3">
      <p className="text-xs leading-tight text-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}

function TodaySkeleton() {
  return (
    <div className="mt-4">
      <div className="grid grid-cols-3 gap-2">
        <Skeleton className="h-16" />
        <Skeleton className="h-16" />
        <Skeleton className="h-16" />
      </div>
      <div className="mt-6 flex flex-col gap-3">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
    </div>
  );
}
