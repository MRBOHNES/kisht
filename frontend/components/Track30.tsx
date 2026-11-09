"use client";

import { useLang } from "@/lib/i18n";

const LIMIT = 30;
const RED_FROM = 25;

/** The 30-day track: one segment per day overdue, last six days red. */
export function Track30({ dpd }: { dpd: number }) {
  const { t } = useLang();
  const left = LIMIT - dpd;
  const near = dpd >= RED_FROM;
  const label =
    left < 0 ? t("trackPast", { gone: dpd })
    : left === 0 ? t("trackTomorrow", { gone: dpd })
    : near ? t("trackNear", { gone: dpd, left })
    : t("trackProgress", { gone: dpd, left });

  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span className="text-muted">{t("trackLimit")}</span>
        <span className={near ? "font-medium text-red" : "text-muted"}>{label}</span>
      </div>
      <div className="flex gap-[2px]" role="img" aria-label={`${t("trackLimit")}: ${label}`}>
        {Array.from({ length: LIMIT }, (_, i) => {
          const day = i + 1;
          const danger = day >= RED_FROM;
          const filled = day <= dpd;
          const colour = filled ? (danger ? "bg-red" : "bg-accent") : danger ? "bg-red-bg" : "bg-line";
          return <span key={day} className={`h-2 flex-1 rounded-[2px] ${colour}`} />;
        })}
      </div>
    </div>
  );
}
