"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";

import { ErrorState, Skeleton } from "@/components/States";
import { ApiError, cachedValue, useApi } from "@/lib/api";
import { addDays, istToday } from "@/lib/dates";
import { useContactHoursOpen } from "@/lib/hooks";
import { useLang } from "@/lib/i18n";
import { mapsUrl } from "@/lib/maps";
import { deleteItem, putItem, syncOutbox, type OutcomeKind as Kind } from "@/lib/outbox";
import { businessLabel, formatDate, formatRupees, rejectionReason, type StringKey } from "@/lib/strings";

export type SheetLoan = {
  loan_id: string;
  business_name: string;
  business_type: string;
  address: string;
  pincode: string;
  outstanding: number;
  emi: number;
};
type Gps = { state: "locating" } | { state: "found"; lat: number; lng: number } | { state: "unavailable" };

const KINDS: { kind: Kind; label: StringKey; tone: string }[] = [
  { kind: "paid", label: "kindPaid", tone: "bg-green-bg text-green" },
  { kind: "promise", label: "kindPromise", tone: "bg-accent/10 text-accent" },
  { kind: "not_reachable", label: "kindNotReachable", tone: "bg-amber-bg text-amber" },
  { kind: "dispute", label: "kindDispute", tone: "bg-red-bg text-red" },
];
const DATE_CHOICES = [1, 3, 7];
const DEFAULT_PROMISE_DAYS = 3;

export function OutcomeSheet() {
  const { id } = useParams<{ id: string }>();
  const { t } = useLang();
  const router = useRouter();
  const { data, error, loading, reload } = useApi<SheetLoan>(`/loans/${encodeURIComponent(id)}`, true);
  // offline and never opened before: the cached Today list has what the sheet needs
  const fromToday =
    error !== undefined && !(error instanceof ApiError)
      ? cachedValue<{ loans: SheetLoan[] }>("/officer/today")?.loans.find((l) => l.loan_id === id)
      : undefined;
  const loan = data ?? fromToday;
  return (
    <main className="pt-4 pb-8">
      <button type="button" onClick={() => router.back()} className="min-h-12 pr-4 text-sm font-medium text-accent">
        ← {t("back")}
      </button>
      {loading && <SheetSkeleton />}
      {error !== undefined && !loading && !loan && <ErrorState message={t("errLoad")} onRetry={reload} />}
      {loan && !loading && <SheetBody loan={loan} onDone={() => router.push("/today")} />}
    </main>
  );
}

export function SheetBody({ loan, onDone }: { loan: SheetLoan; onDone: () => void }) {
  const { t, lang } = useLang();
  const hoursOpen = useContactHoursOpen();
  const gps = useGps();
  // one id per sheet, so retrying after a network error can never log the outcome twice
  const [outcomeId] = useState(() => crypto.randomUUID());
  const [today] = useState(istToday);
  const [kind, setKind] = useState<Kind | null>(null);
  const [amountChoice, setAmountChoice] = useState<"emi" | "double" | "other">("emi");
  const [otherAmount, setOtherAmount] = useState("");
  const [days, setDays] = useState<number | "other">(DEFAULT_PROMISE_DAYS);
  const [otherDate, setOtherDate] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState<{ queued: boolean; outOfWindow: boolean } | null>(null);

  const needsAmount = kind === "paid" || kind === "promise";
  const amount =
    amountChoice === "emi" ? loan.emi : amountChoice === "double" ? loan.emi * 2 : Number(otherAmount || 0);
  const promiseDate = days === "other" ? otherDate : addDays(today, days);
  const canSave =
    kind !== null && !saving && (!needsAmount || amount > 0) && (kind !== "promise" || promiseDate !== "");

  // Saved on the phone first, then sent; without network it waits in the outbox.
  async function save() {
    if (!kind) return;
    setSaving(true);
    setError("");
    try {
      await putItem({
        id: outcomeId,
        loan_id: loan.loan_id,
        kind,
        amount: needsAmount ? Math.round(amount * 100) / 100 : null,
        promise_date: kind === "promise" ? promiseDate : null,
        lat: gps.state === "found" ? gps.lat : null,
        lng: gps.state === "found" ? gps.lng : null,
        logged_at_device: new Date().toISOString(),
        business_name: loan.business_name,
        business_type: loan.business_type,
        state: "pending",
        out_of_window: null,
        error_code: null,
        synced_at: null,
      });
    } catch {
      setError(t("errStorage"));
      setSaving(false);
      return;
    }
    const queued = { queued: true, outOfWindow: hoursOpen === false };
    try {
      const result = navigator.onLine ? (await syncOutbox()).get(outcomeId) : undefined;
      if (result?.status === "rejected") {
        // not stored by the server: take it off the phone so the officer can correct and save again
        await deleteItem(outcomeId);
        setError(t("errSaveRejected", { reason: t(rejectionReason(result.code)) }));
      } else {
        setSaved(result ? { queued: false, outOfWindow: Boolean(result.out_of_window) } : queued);
      }
    } catch {
      setSaved(queued);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <section className="card p-4">
        <p className="font-semibold leading-snug">{businessLabel(loan.business_name, loan.business_type, lang)}</p>
        <p className="text-sm text-muted">
          {loan.loan_id} · {formatRupees(loan.outstanding)}
        </p>
        <a
          href={mapsUrl(loan.address, loan.pincode)}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 flex min-h-12 items-center text-sm text-accent"
        >
          {loan.address || loan.pincode} · {t("map")} ↗
        </a>
      </section>

      {saved ? (
        <section className="card p-5 text-center" role="status">
          <p className={`text-lg font-semibold ${saved.queued ? "text-amber" : "text-green"}`}>
            {saved.queued ? t("savedOnPhone") : t("savedTitle")}
          </p>
          {saved.outOfWindow && <p className="mt-2 text-sm text-amber">{t("savedOutOfWindow")}</p>}
          <button type="button" onClick={onDone} className="mt-4 min-h-12 w-full rounded-xl bg-accent font-medium text-white">
            {t("backToToday")}
          </button>
        </section>
      ) : (
        <section className="card p-4">
          <h1 className="font-semibold">{t("logOutcome")}</h1>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {KINDS.map((k) => (
              <button
                key={k.kind}
                type="button"
                aria-pressed={kind === k.kind}
                onClick={() => setKind(k.kind)}
                className={`min-h-16 rounded-xl px-2 font-medium ${k.tone} ${
                  kind === k.kind ? "ring-2 ring-current ring-offset-2" : ""
                }`}
              >
                {t(k.label)}
              </button>
            ))}
          </div>

          {needsAmount && (
            <fieldset className="mt-4">
              <legend className="text-sm font-medium">{t("amount")}</legend>
              <div className="mt-2 flex flex-wrap gap-2">
                <Chip on={amountChoice === "emi"} onClick={() => setAmountChoice("emi")}>
                  {t("chipEmi", { amount: formatRupees(loan.emi) })}
                </Chip>
                {kind === "promise" && (
                  <Chip on={amountChoice === "double"} onClick={() => setAmountChoice("double")}>
                    {t("chip2Emi", { amount: formatRupees(loan.emi * 2) })}
                  </Chip>
                )}
                <Chip on={amountChoice === "other"} onClick={() => setAmountChoice("other")}>
                  {t("chipOther")}
                </Chip>
              </div>
              {amountChoice === "other" && (
                <input
                  type="number" inputMode="decimal" min="1" step="1" value={otherAmount} aria-label={t("amount")}
                  onChange={(e) => setOtherAmount(e.target.value)}
                  className="mt-2 min-h-12 w-full rounded-xl border border-line px-3"
                />
              )}
              {amountChoice === "other" && otherAmount !== "" && !(amount > 0) && (
                <p className="mt-1 text-sm text-red">{t("amountInvalid")}</p>
              )}
            </fieldset>
          )}

          {kind === "promise" && (
            <fieldset className="mt-4">
              <legend className="text-sm font-medium">{t("promiseDate")}</legend>
              <div className="mt-2 flex flex-wrap gap-2">
                {DATE_CHOICES.map((n) => (
                  <Chip key={n} on={days === n} onClick={() => setDays(n)}>
                    {t("inDays", { n, date: formatDate(addDays(today, n), lang) })}
                  </Chip>
                ))}
                <Chip on={days === "other"} onClick={() => setDays("other")}>
                  {t("chipOther")}
                </Chip>
              </div>
              {days === "other" && (
                <input
                  type="date" min={today} max={addDays(today, 30)} value={otherDate} aria-label={t("promiseDate")}
                  onChange={(e) => setOtherDate(e.target.value)}
                  className="mt-2 min-h-12 w-full rounded-xl border border-line px-3"
                />
              )}
            </fieldset>
          )}

          {kind === "dispute" && <p className="mt-4 rounded-xl bg-red-bg p-3 text-sm text-red">{t("disputeNote")}</p>}

          <div className="mt-4 space-y-1 text-xs text-muted">
            <p>
              {gps.state === "locating" ? t("gpsLocating") : gps.state === "found" ? t("gpsFound") : t("gpsUnavailable")}
            </p>
            {hoursOpen === false && <p className="text-amber">{t("outsideHoursNote")}</p>}
          </div>

          {error && (
            <p role="alert" className="mt-3 rounded-xl bg-red-bg p-3 text-sm text-red">
              {error}
            </p>
          )}
          <button
            type="button"
            onClick={save}
            disabled={!canSave}
            className="mt-4 min-h-12 w-full rounded-xl bg-accent font-medium text-white disabled:opacity-40"
          >
            {saving ? t("saving") : t("save")}
          </button>
        </section>
      )}
    </div>
  );
}

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={`min-h-12 rounded-full border px-4 text-sm ${on ? "border-accent bg-accent text-white" : "border-line bg-card"}`}
    >
      {children}
    </button>
  );
}

function subscribeNever() {
  return () => {};
}

function useGps(): Gps {
  const supported = useSyncExternalStore(subscribeNever, () => "geolocation" in navigator, () => true);
  const [gps, setGps] = useState<Gps>({ state: "locating" });
  useEffect(() => {
    if (!("geolocation" in navigator)) return;
    navigator.geolocation.getCurrentPosition(
      (position) => setGps({ state: "found", lat: position.coords.latitude, lng: position.coords.longitude }),
      () => setGps({ state: "unavailable" }),
      { enableHighAccuracy: true, timeout: 10_000, maximumAge: 60_000 },
    );
  }, []);
  return supported ? gps : { state: "unavailable" };
}

export function SheetSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      <Skeleton className="h-28" />
      <Skeleton className="h-64" />
    </div>
  );
}
