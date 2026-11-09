"use client";

import { useState, useSyncExternalStore } from "react";

import { BottomTabs } from "@/components/BottomTabs";
import { LangToggle } from "@/components/LangToggle";
import { useOnline } from "@/lib/hooks";
import { useLang } from "@/lib/i18n";
import { deleteItem, syncOutbox, useOutbox, type OutboxItem } from "@/lib/outbox";
import { businessLabel, formatDateTime, formatRupees, formatTime, rejectionReason, type StringKey } from "@/lib/strings";

const KIND_LABEL: Record<OutboxItem["kind"], StringKey> = {
  paid: "kindPaid",
  promise: "kindPromise",
  not_reachable: "kindNotReachable",
  dispute: "kindDispute",
};

function subscribeStorage(callback: () => void) {
  window.addEventListener("kisht-outbox-changed", callback);
  return () => window.removeEventListener("kisht-outbox-changed", callback);
}

export default function SyncPage() {
  const { t, lang } = useLang();
  const online = useOnline();
  const items = useOutbox();
  const lastSync = useSyncExternalStore(subscribeStorage, () => window.localStorage.getItem("kisht.lastSync"), () => null);
  const [syncing, setSyncing] = useState(false);
  const [failed, setFailed] = useState(false);

  const pending = items.filter((i) => i.state === "pending");
  const rejected = items.filter((i) => i.state === "rejected");
  const sent = items.filter((i) => i.state === "sent");
  const flagged = sent.filter((i) => i.out_of_window);

  async function syncNow() {
    setSyncing(true);
    setFailed(false);
    try {
      await syncOutbox();
    } catch {
      setFailed(true);
    } finally {
      setSyncing(false);
    }
  }

  return (
    <main className="pt-4 pb-20">
      <header className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">{t("syncTitle")}</h1>
        <LangToggle />
      </header>

      <section className={`card mt-4 p-4 ${online ? "" : "border-amber"}`}>
        <p className={`font-medium ${online ? "text-green" : "text-amber"}`}>{online ? t("online") : t("offline")}</p>
        <p className="mt-1 text-sm text-muted">{online ? t("syncOnline") : t("syncOffline")}</p>
        {lastSync && <p className="mt-1 text-xs text-muted">{t("lastSync", { time: formatTime(lastSync, lang) })}</p>}
        <button
          type="button"
          onClick={syncNow}
          disabled={!online || syncing || pending.length === 0}
          className="mt-3 min-h-12 w-full rounded-xl bg-accent font-medium text-white disabled:opacity-40"
        >
          {syncing ? t("syncing") : t("syncNow")} {pending.length > 0 && `(${pending.length})`}
        </button>
        {failed && <p className="mt-2 text-sm text-red">{t("syncFailed")}</p>}
      </section>

      <Section title={t("sectionPending")} empty={t("emptyPending")} items={pending} />
      {rejected.length > 0 && (
        <Section
          title={t("sectionRejected")}
          items={rejected}
          extra={(item) => (
            <div className="mt-1 flex items-center justify-between gap-2">
              <p className="text-xs text-red">{t(rejectionReason(item.error_code))}</p>
              <button type="button" onClick={() => deleteItem(item.id)} className="min-h-12 px-2 text-sm text-accent">
                {t("dismiss")}
              </button>
            </div>
          )}
        />
      )}
      {flagged.length > 0 && <Section title={t("sectionFlagged")} items={flagged} />}
      <Section title={t("sectionSent")} empty={t("emptySent")} items={sent} />
      <BottomTabs />
    </main>
  );

}

function Section({ title, empty, items, extra }: {
  title: string;
  empty?: string;
  items: OutboxItem[];
  extra?: (item: OutboxItem) => React.ReactNode;
}) {
  const { t, lang } = useLang();
  return (
    <section className="mt-5">
      <h2 className="mb-2 font-semibold">
        {title} ({items.length})
      </h2>
      {items.length === 0 ? (
        <p className="card p-4 text-sm text-muted">{empty}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {items.map((item) => (
            <li key={item.id} className="card p-3">
              <div className="flex justify-between gap-2">
                <p className="text-sm font-medium">{businessLabel(item.business_name, item.business_type, lang)}</p>
                {item.amount !== null && <p className="text-sm font-semibold">{formatRupees(item.amount)}</p>}
              </div>
              <p className="text-xs text-muted">
                {item.loan_id} · {t(KIND_LABEL[item.kind])} · {formatDateTime(item.logged_at_device, lang)}
              </p>
              {item.out_of_window && (
                <span className="mt-1 inline-block rounded-full bg-amber-bg px-2 py-0.5 text-xs text-amber">{t("flaggedChip")}</span>
              )}
              {extra?.(item)}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
