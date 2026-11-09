"use client";

import { useEffect, useState } from "react";

import { api } from "./api";

export type OutcomeKind = "paid" | "promise" | "not_reachable" | "dispute";

export type OutboxItem = {
  id: string; // generated on the phone; the server ignores a repeat
  loan_id: string;
  kind: OutcomeKind;
  amount: number | null;
  promise_date: string | null;
  lat: number | null;
  lng: number | null;
  logged_at_device: string;
  business_name: string;
  business_type: string;
  state: "pending" | "sent" | "rejected";
  out_of_window: boolean | null;
  error_code: string | null;
  synced_at: string | null;
};

type SyncResult = { id: string; status: "saved" | "duplicate" | "rejected"; out_of_window?: boolean | null; code?: string };

const DB_NAME = "kisht";
const STORE = "outbox";
const CHANGED = "kisht-outbox-changed";
const BATCH = 100;
const KEEP_SENT = 50;

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE, { keyPath: "id" });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function run<T>(mode: IDBTransactionMode, action: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, mode);
    const request = action(tx.objectStore(STORE));
    tx.oncomplete = () => {
      db.close();
      resolve(request.result);
    };
    tx.onerror = () => reject(tx.error);
  });
}

function changed() {
  window.dispatchEvent(new Event(CHANGED));
}

export async function listItems(): Promise<OutboxItem[]> {
  const items = await run("readonly", (store) => store.getAll() as IDBRequest<OutboxItem[]>);
  return items.sort((a, b) => b.logged_at_device.localeCompare(a.logged_at_device));
}

export async function putItem(item: OutboxItem): Promise<void> {
  await run("readwrite", (store) => store.put(item));
  changed();
}

export async function deleteItem(id: string): Promise<void> {
  await run("readwrite", (store) => store.delete(id));
  changed();
}

function payload(item: OutboxItem) {
  const { id, loan_id, kind, amount, promise_date, lat, lng, logged_at_device } = item;
  return { id, loan_id, kind, amount, promise_date, lat, lng, logged_at_device };
}

async function sendPending(): Promise<Map<string, SyncResult>> {
  const results = new Map<string, SyncResult>();
  let pending = (await listItems()).filter((i) => i.state === "pending");
  while (pending.length > 0) {
    const batch = pending.slice(0, BATCH);
    const response = await api<{ results: SyncResult[] }>("/sync", {
      method: "POST",
      body: JSON.stringify({ outcomes: batch.map(payload) }),
    });
    const now = new Date().toISOString();
    for (const result of response.results) {
      results.set(result.id, result);
      const item = batch.find((i) => i.id === result.id);
      if (!item) continue;
      await putItem(
        result.status === "rejected"
          ? { ...item, state: "rejected", error_code: result.code ?? "invalid", synced_at: now }
          : { ...item, state: "sent", out_of_window: result.out_of_window ?? item.out_of_window, synced_at: now },
      );
    }
    pending = pending.slice(BATCH);
  }
  await pruneSent();
  window.localStorage.setItem("kisht.lastSync", new Date().toISOString());
  changed();
  return results;
}

async function pruneSent() {
  const sent = (await listItems()).filter((i) => i.state === "sent");
  for (const old of sent.slice(KEEP_SENT)) await deleteItem(old.id);
}

let inFlight: Promise<Map<string, SyncResult>> | null = null;

/** Sends every pending item. A call made while a sync is running waits for it, then sends what is left. */
export async function syncOutbox(): Promise<Map<string, SyncResult>> {
  if (inFlight) await inFlight.catch(() => undefined);
  inFlight = sendPending().finally(() => {
    inFlight = null;
  });
  return inFlight;
}

export function useOutbox(): OutboxItem[] {
  const [items, setItems] = useState<OutboxItem[]>([]);
  useEffect(() => {
    let alive = true;
    const load = () =>
      listItems().then(
        (list) => alive && setItems(list),
        () => undefined,
      );
    load();
    window.addEventListener(CHANGED, load);
    return () => {
      alive = false;
      window.removeEventListener(CHANGED, load);
    };
  }, []);
  return items;
}
