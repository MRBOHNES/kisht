"use client";

import { useLang } from "@/lib/i18n";

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-2xl bg-line ${className}`} aria-hidden />;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  const { t } = useLang();
  return (
    <div className="card p-5 text-center" role="alert">
      <p className="text-sm text-muted">{message}</p>
      <button type="button" onClick={onRetry} className="mt-3 min-h-12 rounded-xl bg-accent px-5 font-medium text-white">
        {t("retry")}
      </button>
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return <div className="card p-6 text-center text-sm text-muted">{message}</div>;
}
