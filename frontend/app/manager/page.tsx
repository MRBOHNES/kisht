"use client";

import { useState } from "react";

import { ManagerNav } from "@/components/ManagerNav";
import { RollChart, type RollStep } from "@/components/RollChart";
import { Sparkline } from "@/components/Sparkline";
import { ErrorState, Skeleton } from "@/components/States";
import { ApiError, api, useApi } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { businessLabel, formatDate, formatDateTime, formatRupees, type StringKey } from "@/lib/strings";

type LoanRow = { loan_id: string; business_name: string; business_type: string; officer: string; dpd: number; outstanding: number };
type Dashboard = {
  roll_rate: { target: number; all: RollStep[]; branches: { branch: string; steps: RollStep[] }[] };
  broken_promises: { count: number; weeks: number[] };
  same_day: { target: number; rate: number | null; logged: number; weeks: (number | null)[] };
  untouched: number;
  attention: {
    about_to_roll: LoanRow[];
    not_kept: { loan_id: string; business_name: string; business_type: string; officer: string; amount: number; promised_date: string }[];
    out_of_hours: { loan_id: string; officer: string; kind: "paid" | "promise" | "not_reachable" | "dispute"; logged_at: string }[];
    disputes: LoanRow[];
  };
  pins: (LoanRow & { reason: string })[];
};

const KIND_LABEL: Record<string, StringKey> = {
  paid: "kindPaid", promise: "kindPromise", not_reachable: "kindNotReachable", dispute: "kindDispute",
};

const pct = (v: number | null) => (v === null ? "–" : `${Math.round(v * 100)}%`);

export default function ManagerDashboard() {
  const { t, lang } = useLang();
  const { data, error, loading, reload } = useApi<Dashboard>("/manager/dashboard");
  const locale = lang === "hi" ? "hi-IN-u-nu-latn" : "en-IN";

  return (
    <>
      <ManagerNav />
      <main className="mx-auto max-w-6xl p-4">
        <h1 className="text-xl font-semibold">{t("dashTitle")}</h1>
        {loading && (
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-28" />)}
            <Skeleton className="h-64 md:col-span-2" />
            <Skeleton className="h-64 md:col-span-2" />
          </div>
        )}
        {error !== undefined && !loading && (
          <div className="mt-4"><ErrorState message={t("errLoad")} onRetry={reload} /></div>
        )}
        {data && !loading && <Body data={data} locale={locale} reload={reload} />}
      </main>
    </>
  );
}

function Body({ data, locale, reload }: { data: Dashboard; locale: string; reload: () => void }) {
  const { t, lang } = useLang();
  const latest = data.roll_rate.all.at(-1)?.rate ?? null;
  const maxBroken = Math.max(1, ...data.broken_promises.weeks);
  const target = data.roll_rate.target;

  return (
    <div className="mt-4 flex flex-col gap-4">
      <section className="grid gap-3 sm:grid-cols-2 md:grid-cols-4">
        <Kpi
          label={t("kpiRollRate")} value={pct(latest)} note={t("targetLabel", { target: pct(target) })}
          bad={latest !== null && latest > target} spark={data.roll_rate.all.map((s) => s.rate)}
        />
        <Kpi label={t("kpiBroken")} value={String(data.broken_promises.count)} spark={data.broken_promises.weeks.map((n) => n / maxBroken)} />
        <Kpi
          label={t("kpiSameDay")} value={data.same_day.rate === null ? t("noData") : pct(data.same_day.rate)}
          note={t("targetLabel", { target: pct(data.same_day.target) })}
          bad={data.same_day.rate !== null && data.same_day.rate < data.same_day.target} spark={data.same_day.weeks}
        />
        <Kpi label={t("kpiUntouched")} value={String(data.untouched)} />
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="card p-4">
          <h2 className="font-semibold">{t("rollChartTitle")}</h2>
          {data.roll_rate.all.length === 0 ? (
            <p className="mt-2 text-sm text-muted">{t("noData")}</p>
          ) : (
            <RollChart steps={data.roll_rate.all} target={target} locale={locale} />
          )}
          <p className="text-xs text-muted">- - {t("targetLabel", { target: pct(target) })}</p>
        </div>
        <div className="card p-4">
          <h2 className="font-semibold">{t("rollByBranch")}</h2>
          <ul className="mt-3 flex flex-col gap-3">
            {data.roll_rate.branches.map((b) => {
              const rate = b.steps.at(-1)?.rate ?? null;
              return (
                <li key={b.branch}>
                  <div className="flex justify-between text-sm">
                    <span>{b.branch}</span>
                    <span className={`font-semibold ${rate !== null && rate > target ? "text-red" : "text-green"}`}>{pct(rate)}</span>
                  </div>
                  <div className="relative mt-1 h-3 rounded-full bg-line">
                    <div
                      className={`h-3 rounded-full ${rate !== null && rate > target ? "bg-red" : "bg-green"}`}
                      style={{ width: `${Math.min(100, ((rate ?? 0) / 0.4) * 100)}%` }}
                    />
                    <div className="absolute top-[-3px] h-[18px] w-0.5 bg-ink" style={{ left: `${(target / 0.4) * 100}%` }} aria-hidden />
                  </div>
                </li>
              );
            })}
          </ul>
          <p className="mt-3 text-xs text-muted">| {t("targetLabel", { target: pct(target) })}</p>
        </div>
      </section>

      <section>
        <h2 className="mb-2 font-semibold">{t("attentionTitle")}</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <Panel title={t("attAboutToRoll")} count={data.attention.about_to_roll.length}>
            {data.attention.about_to_roll.map((loan) => (
              <PinRow key={loan.loan_id} loan={loan} onPinned={reload} />
            ))}
          </Panel>
          <Panel title={t("pinnedTitle")} count={data.pins.length}>
            {data.pins.map((loan) => (
              <li key={loan.loan_id} className="flex items-center justify-between gap-2 py-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{businessLabel(loan.business_name, loan.business_type, lang)}</p>
                  <p className="text-xs text-muted">{loan.loan_id} · {loan.officer} · {loan.reason}</p>
                </div>
                <button
                  type="button"
                  onClick={() => api(`/manager/pins/${encodeURIComponent(loan.loan_id)}`, { method: "DELETE" }).then(reload, reload)}
                  className="min-h-12 shrink-0 px-3 text-sm text-accent"
                >
                  {t("unpin")}
                </button>
              </li>
            ))}
          </Panel>
          <Panel title={t("attNotKept")} count={data.attention.not_kept.length}>
            {data.attention.not_kept.map((p) => (
              <li key={`${p.loan_id}${p.promised_date}`} className="flex justify-between gap-2 py-2 text-sm">
                <span className="min-w-0 truncate">{businessLabel(p.business_name, p.business_type, lang)} · {p.loan_id} · {p.officer}</span>
                <span className="shrink-0">{formatRupees(p.amount)} · {formatDate(p.promised_date, lang)}</span>
              </li>
            ))}
          </Panel>
          <Panel title={t("attOutOfHours")} count={data.attention.out_of_hours.length}>
            {data.attention.out_of_hours.map((o) => (
              <li key={`${o.loan_id}${o.logged_at}`} className="flex justify-between gap-2 py-2 text-sm">
                <span>{o.loan_id} · {o.officer} · {t(KIND_LABEL[o.kind])}</span>
                <span className="shrink-0 text-amber">{formatDateTime(o.logged_at, lang)}</span>
              </li>
            ))}
          </Panel>
          <Panel title={t("paused")} count={data.attention.disputes.length}>
            {data.attention.disputes.map((loan) => (
              <li key={loan.loan_id} className="flex justify-between gap-2 py-2 text-sm">
                <span className="min-w-0 truncate">{businessLabel(loan.business_name, loan.business_type, lang)} · {loan.loan_id} · {loan.officer}</span>
                <span className="shrink-0">{formatRupees(loan.outstanding)}</span>
              </li>
            ))}
          </Panel>
        </div>
      </section>
    </div>
  );
}

function Kpi({ label, value, note, bad, spark }: { label: string; value: string; note?: string; bad?: boolean; spark?: (number | null)[] }) {
  return (
    <div className="card flex items-end justify-between gap-2 p-4">
      <div>
        <p className="text-xs text-muted">{label}</p>
        <p className={`mt-1 text-2xl font-semibold ${bad ? "text-red" : ""}`}>{value}</p>
        {note && <p className="text-xs text-muted">{note}</p>}
      </div>
      {spark && <Sparkline values={spark} />}
    </div>
  );
}

function Panel({ title, count, children }: { title: string; count: number; children: React.ReactNode }) {
  const { t } = useLang();
  return (
    <div className="card p-4">
      <h3 className="text-sm font-semibold">{title} ({count})</h3>
      {count === 0 ? <p className="mt-2 text-sm text-muted">{t("emptyAttention")}</p> : <ul className="mt-1 divide-y divide-line">{children}</ul>}
    </div>
  );
}

function PinRow({ loan, onPinned }: { loan: LoanRow; onPinned: () => void }) {
  const { t, lang } = useLang();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  async function pin(event: React.FormEvent) {
    event.preventDefault();
    try {
      await api("/manager/pins", { method: "POST", body: JSON.stringify({ loan_id: loan.loan_id, reason }) });
      onPinned();
    } catch (e) {
      setError(e instanceof ApiError ? t("errGeneric") : t("errNetwork"));
    }
  }

  return (
    <li className="py-2">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{businessLabel(loan.business_name, loan.business_type, lang)}</p>
          <p className="text-xs text-muted">
            {loan.loan_id} · {loan.officer} · <span className="text-red">{t("daysOverdue", { n: loan.dpd })}</span> · {formatRupees(loan.outstanding)}
          </p>
        </div>
        {!open && (
          <button type="button" onClick={() => setOpen(true)} className="min-h-12 shrink-0 rounded-xl border border-line px-3 text-sm font-medium text-accent">
            {t("pin")}
          </button>
        )}
      </div>
      {open && (
        <form onSubmit={pin} className="mt-2 flex flex-wrap gap-2">
          <input
            value={reason} onChange={(e) => setReason(e.target.value)} required minLength={3} maxLength={200}
            placeholder={t("pinReason")} aria-label={t("pinReason")}
            className="min-h-12 min-w-0 flex-1 rounded-xl border border-line px-3 text-sm"
          />
          <button type="submit" className="min-h-12 rounded-xl bg-accent px-4 text-sm font-medium text-white">{t("pin")}</button>
          <button type="button" onClick={() => setOpen(false)} className="min-h-12 px-3 text-sm text-muted">{t("cancel")}</button>
          {error && <p className="w-full text-sm text-red">{error}</p>}
        </form>
      )}
    </li>
  );
}
