"use client";

import Link from "next/link";

import { Track30 } from "@/components/Track30";
import { useLang } from "@/lib/i18n";
import { businessLabel, formatRupees } from "@/lib/strings";

export type Reason = { key: string; points: number; text_en: string; text_hi: string };

export type LoanCardData = {
  rank: number;
  loan_id: string;
  business_name: string;
  business_type: string;
  outstanding: number;
  dpd: number;
  low_confidence: boolean;
  top_reason: Reason | null;
};

export function LoanCard({ loan }: { loan: LoanCardData }) {
  const { t, lang } = useLang();
  const reason = loan.top_reason ? (lang === "hi" ? loan.top_reason.text_hi : loan.top_reason.text_en) : "";
  return (
    <Link href={`/loan/${loan.loan_id}`} className="card block p-4 active:bg-bg">
      <div className="flex items-start gap-3">
        <span className="flex h-8 min-w-8 items-center justify-center rounded-full bg-accent/10 text-sm font-semibold text-accent">
          {loan.rank}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <p className="font-medium leading-snug">{businessLabel(loan.business_name, loan.business_type, lang)}</p>
            <p className="shrink-0 font-semibold">{formatRupees(loan.outstanding)}</p>
          </div>
          <p className="mt-0.5 text-sm text-muted">
            {loan.loan_id} · {reason}
          </p>
          {loan.low_confidence && (
            <span className="mt-2 inline-block rounded-full bg-amber-bg px-2 py-0.5 text-xs font-medium text-amber">
              {t("lowConfidence")}
            </span>
          )}
        </div>
      </div>
      <div className="mt-3">
        <Track30 dpd={loan.dpd} />
      </div>
    </Link>
  );
}
