"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { LangToggle } from "@/components/LangToggle";
import { ApiError, api } from "@/lib/api";
import { useLang } from "@/lib/i18n";

type Me = { role: "field_officer" | "branch_manager" };

// Illustration on the brand panel only; real figures are behind sign-in.
const SAMPLE_ROLL = [0.24, 0.21, 0.22];

export default function ManagerLogin() {
  const { t, lang } = useLang();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const me = await api<Me>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
      router.replace(me.role === "branch_manager" ? "/manager" : "/today");
    } catch (e) {
      if (!(e instanceof ApiError)) setError(t("errNetwork"));
      else if (e.status === 423) {
        const until = (e.detail as { locked_until?: string })?.locked_until ?? "";
        const time = until
          ? new Date(until).toLocaleTimeString(lang === "hi" ? "hi-IN-u-nu-latn" : "en-IN", {
              timeZone: "Asia/Kolkata", hour: "numeric", minute: "2-digit",
            })
          : "";
        setError(t("errLocked", { time }));
      } else setError(e.status === 401 ? t("errInvalid") : t("errGeneric"));
      setBusy(false);
    }
  }

  return (
    <main className="grid min-h-screen md:grid-cols-2">
      <section className="flex flex-col justify-between bg-ink p-8 text-white">
        <div>
          <p className="text-2xl font-semibold">Kisht</p>
          <p className="mt-1 text-sm text-white/70">{t("mgrBrandLine")}</p>
        </div>
        <div className="mt-10 max-w-sm rounded-2xl bg-white/10 p-5">
          <p className="text-xs text-white/70">{t("mgrSampleRoll")}</p>
          <p className="mt-1 text-3xl font-semibold">22%</p>
          <p className="text-xs text-white/70">{t("mgrVsTarget", { target: "16%" })}</p>
          <div className="mt-4 flex h-16 items-end gap-3" aria-hidden>
            {SAMPLE_ROLL.map((rate, i) => (
              <div key={i} className="flex-1 rounded-t bg-white/60" style={{ height: `${rate * 250}%` }} />
            ))}
          </div>
        </div>
        <p className="mt-8 text-xs text-white/60">{t("dpdpNote")}</p>
      </section>

      <section className="flex flex-col p-6 md:p-12">
        <div className="flex justify-end">
          <LangToggle />
        </div>
        <form onSubmit={submit} className="mx-auto mt-10 flex w-full max-w-sm flex-col gap-4">
          <h1 className="text-xl font-semibold">{t("mgrLoginTitle")}</h1>
          <label className="flex flex-col gap-1 text-sm font-medium">
            {t("email")}
            <input
              type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)}
              className="min-h-12 rounded-xl border border-line bg-card px-3 text-base font-normal"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium">
            {t("password")}
            <div className="flex rounded-xl border border-line bg-card">
              <input
                type={showPassword ? "text" : "password"} required autoComplete="current-password" value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="min-h-12 min-w-0 flex-1 rounded-xl px-3 text-base font-normal outline-none"
              />
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="min-h-12 px-3 text-sm text-accent">
                {showPassword ? t("hide") : t("show")}
              </button>
            </div>
          </label>
          {error && <p role="alert" className="rounded-xl bg-red-bg p-3 text-sm text-red">{error}</p>}
          <button type="submit" disabled={busy} className="min-h-12 rounded-xl bg-accent font-medium text-white disabled:opacity-60">
            {busy ? t("signingIn") : t("signIn")}
          </button>
          <p className="text-sm text-muted">{t("forgot")}</p>
          <p className="rounded-xl bg-amber-bg p-3 text-xs text-amber">{t("mgrDemoNote")}</p>
        </form>
      </section>
    </main>
  );
}
