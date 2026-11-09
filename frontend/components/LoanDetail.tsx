"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { LangToggle } from "@/components/LangToggle";
import type { Reason } from "@/components/LoanCard";
import { ErrorState, Skeleton } from "@/components/States";
import { Track30 } from "@/components/Track30";
import { ApiError, useApi } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { businessLabel, formatDate, formatDateTime, formatRupees } from "@/lib/strings";

type Detail = {
  loan_id: string;
  status: "active" | "paused_dispute" | "cured";
  business_name: string;
  business_type: string;
  outstanding: number;
  emi: number;
  dpd: number;
  last_payment_date: string | null;
  score: {
    risk: number;
    priority: number;
    amount_factor: number;
    self_cure: "paid_recently" | "promise_pending" | null;
    low_confidence: boolean;
    reasons: Reason[];
  };
  contact_attempts: { type: "call" | "visit"; at: string; allowed: boolean; blocked_reason: string | null }[];
};

// Bars are drawn against the largest factor (roll risk, 35 points)
const MAX_FACTOR_POINTS = 35;

export function LoanDetail() {
  const { id } = useParams<{ id: string }>();
  const { t } = useLang();
  const { data, error, loading, reload } = useApi<Detail>(`/loans/${encodeURIComponent(id)}`);

  return (
    <main className="pt-4">
      <header className="flex items-center justify-between">
        <Link href="/today" className="flex min-h-12 items-center pr-4 text-sm font-medium text-accent">
          ← {t("back")}
        </Link>
        <LangToggle />
      </header>
      {loading && <DetailSkeleton />}
      {error !== undefined && !loading && (
        <div className="mt-4">
          {error instanceof ApiError && error.status === 404 ? (
            <div className="card p-6 text-center text-sm text-muted">{t("notFound")}</div>
          ) : (
            <ErrorState message={t("errLoad")} onRetry={reload} />
          )}
        </div>
      )}
      {data && !loading && <DetailBody loan={data} />}
    </main>
  );
}

function DetailBody({ loan }: { loan: Detail }) {
  const { t, lang } = useLang();
  const { score } = loan;
  const why = score.self_cure === "paid_recently" ? t("selfCurePaid") : t("selfCurePromise");
  const explanation =
    t("explain", { priority: score.priority, risk: score.risk, factor: score.amount_factor.toFixed(2) }) +
    (score.self_cure ? t("halved", { why }) : "");

  return (
    <div className="mt-2 flex flex-col gap-3">
      <section className="card p-4">
        <h1 className="font-semibold leading-snug">{businessLabel(loan.business_name, loan.business_type, lang)}</h1>
        <p className="text-sm text-muted">{loan.loan_id}</p>
        {loan.status !== "active" && (
          <span className="mt-2 inline-block rounded-full bg-amber-bg px-2 py-0.5 text-xs font-medium text-amber">
            {loan.status === "paused_dispute" ? t("paused") : t("cured")}
          </span>
        )}
        <div className="mt-3 flex items-end justify-between">
          <div>
            <p className="text-xs text-muted">{t("outstanding")}</p>
            <p className="text-2xl font-semibold">{formatRupees(loan.outstanding)}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted">{t("emi")}</p>
            <p className="font-medium">{formatRupees(loan.emi)}</p>
          </div>
        </div>
        <p className="mt-1 text-xs text-muted">
          {loan.last_payment_date ? t("lastPaid", { date: formatDate(loan.last_payment_date, lang) }) : t("neverPaid")}
        </p>
        <div className="mt-3">
          <Track30 dpd={loan.dpd} />
        </div>
        <p className="mt-3 text-sm text-muted">{explanation}</p>
      </section>

      <section className="card p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">{t("keyInfo")}</h2>
          <span className="rounded-full bg-bg px-3 py-1 text-xs text-muted">{t("advisory")}</span>
        </div>
        <p className="mt-2 text-sm text-muted">
          {t("riskScore")} <span className="text-lg font-semibold text-ink">{score.risk}</span>/100
        </p>
        {score.low_confidence && (
          <p className="mt-2 rounded-xl bg-amber-bg p-3 text-xs text-amber">
            <span className="font-medium">{t("lowConfidence")}:</span> {t("lowConfidenceNote")}
          </p>
        )}
        <ul className="mt-3 flex flex-col gap-3">
          {score.reasons.map((reason) => (
            <li key={reason.key}>
              <div className="flex justify-between gap-3 text-sm">
                <span>{lang === "hi" ? reason.text_hi : reason.text_en}</span>
                <span className="shrink-0 font-medium">+{reason.points}</span>
              </div>
              <div className="mt-1 h-1.5 rounded-full bg-line">
                <div
                  className="h-1.5 rounded-full bg-accent"
                  style={{ width: `${Math.min(100, (reason.points / MAX_FACTOR_POINTS) * 100)}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="card p-4">
        <h2 className="font-semibold">{t("contactRecord")}</h2>
        {loan.contact_attempts.length === 0 ? (
          <p className="mt-2 text-sm text-muted">{t("contactEmpty")}</p>
        ) : (
          <ul className="mt-2 divide-y divide-line">
            {loan.contact_attempts.map((attempt) => (
              <li key={attempt.at + attempt.type} className="flex justify-between gap-3 py-2 text-sm">
                <span>
                  {attempt.type === "call" ? t("call") : t("visit")} · {formatDateTime(attempt.at, lang)}
                </span>
                {attempt.allowed ? (
                  <span className="text-green">{t("done")}</span>
                ) : (
                  <span className="text-right text-red">{t("blocked", { reason: attempt.blocked_reason ?? "" })}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export function DetailSkeleton() {
  return (
    <div className="mt-2 flex flex-col gap-3">
      <Skeleton className="h-56" />
      <Skeleton className="h-48" />
      <Skeleton className="h-24" />
    </div>
  );
}
