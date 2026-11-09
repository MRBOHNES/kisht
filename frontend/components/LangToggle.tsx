"use client";

import { useLang } from "@/lib/i18n";

export function LangToggle() {
  const { lang, setLang, t } = useLang();
  return (
    <button
      type="button"
      onClick={() => setLang(lang === "hi" ? "en" : "hi")}
      className="min-h-12 min-w-12 rounded-full border border-line bg-card px-4 text-sm font-medium text-ink"
    >
      {t("switchLang")}
    </button>
  );
}
