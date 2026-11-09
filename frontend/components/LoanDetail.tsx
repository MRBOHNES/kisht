"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { LangToggle } from "@/components/LangToggle";
import type { Reason } from "@/components/LoanCard";
import { ErrorState, Skeleton } from "@/components/States";
import { Track30 } from "@/components/Track30";
import { ApiError, api, useApi } from "@/lib/api";
import { useContactHoursOpen } from "@/lib/hooks";
import { useLang } from "@/lib/i18n";
import { mapsUrl } from "@/lib/maps";
import { businessLabel, formatDate, formatDateTime, formatRupees } from "@/lib/strings";

type Detail = {
  loan_id: string;
  status: "active" | "paused_dispute" | "cured";
  business_name: string;
  business_type: string;
  address: string;
  pincode: string;
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
  contact_attempts: Attempt[];
};

type Attempt = { type: "call" | "visit"; at: string; allowed: boolean; blocked_reason: string | null };

// Bars are drawn against the largest factor (roll risk, 35 points)
const MAX_FACTOR_POINTS = 35;

export function LoanDetail() {
  const { id } = useParams<{ id: string }>();
  const { t } = useLang();
  const { data, error, loading, reload } = useApi<Detail>(`/loans/${encodeURIComponent(id)}`);

  return (
    <main className="pt-4 pb-28">
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
  const [attempts, setAttempts] = useState(loan.contact_attempts);
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
        {attempts.length === 0 ? (
          <p className="mt-2 text-sm text-muted">{t("contactEmpty")}</p>
        ) : (
          <ul className="mt-2 divide-y divide-line">
            {attempts.map((attempt) => (
              <li key={attempt.at + attempt.type} className="flex justify-between gap-3 py-2 text-sm">
                <span>
                  {attempt.type === "call" ? t("call") : t("visit")} · {formatDateTime(attempt.at, lang)}
                </span>
                {attempt.allowed ? (
                  <span className="text-green">{t("done")}</span>
                ) : (
                  <span className="text-right text-red">{t("blocked", { reason: t("contactRule") })}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
      <ActionBar loan={loan} onAttempt={(a) => setAttempts((list) => [a, ...list])} />
    </div>
  );
}

function ActionBar({ loan, onAttempt }: { loan: Detail; onAttempt: (a: Attempt) => void }) {
  const { t } = useLang();
  const hoursOpen = useContactHoursOpen();
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState("");

  // The button stays tappable outside hours: the server decides and records the blocked attempt.
  async function callBorrower() {
    setChecking(true);
    setMessage("");
    try {
      const result = await api<{ phone: string; attempt: Attempt }>(`/loans/${encodeURIComponent(loan.loan_id)}/contact`, {
        method: "POST",
        body: JSON.stringify({ type: "call" }),
      });
      onAttempt(result.attempt);
      window.location.href = `tel:${result.phone}`;
    } catch (e) {
      const detail = e instanceof ApiError ? (e.detail as { code?: string; attempt?: Attempt }) : undefined;
      if (detail?.code === "outside_contact_hours" && detail.attempt) {
        onAttempt(detail.attempt);
        setMessage(t("callBlocked"));
      } else {
        setMessage(e instanceof ApiError ? t("errGeneric") : t("errNetwork"));
      }
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="fixed inset-x-0 bottom-0 border-t border-line bg-bg/95 backdrop-blur">
      <div className="mx-auto w-full max-w-[420px] px-4 pt-2 pb-4">
        {message && (
          <p role="status" className="mb-2 rounded-xl bg-red-bg p-3 text-sm text-red">
            {message}
          </p>
        )}
        <div className="grid grid-cols-[1fr_1fr_1.6fr] gap-2">
          <button
            type="button"
            onClick={callBorrower}
            disabled={checking}
            className={`min-h-12 rounded-xl border border-line px-2 text-sm font-medium ${
              hoursOpen === false ? "bg-bg text-muted" : "bg-card text-ink"
            }`}
          >
            {checking ? t("checking") : t("call")}
            {hoursOpen === false && <span className="block text-[10px] leading-tight">{t("contactRule")}</span>}
          </button>
          <a
            href={mapsUrl(loan.address, loan.pincode)}
            target="_blank"
            rel="noopener noreferrer"
            className="flex min-h-12 items-center justify-center rounded-xl border border-line bg-card text-sm font-medium"
          >
            {t("map")}
          </a>
          <Link
            href={`/loan/${encodeURIComponent(loan.loan_id)}/log`}
            className="flex min-h-12 items-center justify-center rounded-xl bg-accent px-2 text-sm font-medium text-white"
          >
            {t("logOutcome")}
          </Link>
        </div>
      </div>
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
