"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { LangToggle } from "@/components/LangToggle";
import { ApiError, api } from "@/lib/api";
import { useLang } from "@/lib/i18n";

type Me = { role: "field_officer" | "branch_manager" };

export default function OfficerLogin() {
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
      // the role comes from the account, never from this page
      router.replace(me.role === "field_officer" ? "/today" : "/manager");
    } catch (e) {
      setError(loginError(e));
      setBusy(false);
    }
  }

  function loginError(e: unknown): string {
    if (!(e instanceof ApiError)) return t("errNetwork");
    const detail = e.detail as { code?: string; locked_until?: string } | undefined;
    if (e.status === 423 && detail?.locked_until) {
      const time = new Date(detail.locked_until).toLocaleTimeString(lang === "hi" ? "hi-IN-u-nu-latn" : "en-IN", {
        timeZone: "Asia/Kolkata", hour: "numeric", minute: "2-digit",
      });
      return t("errLocked", { time });
    }
    return e.status === 401 ? t("errInvalid") : t("errGeneric");
  }

  return (
    <main className="flex min-h-screen flex-col pt-4">
      <div className="flex justify-end">
        <LangToggle />
      </div>
      <div className="mt-10 mb-8">
        <p className="text-2xl font-semibold text-accent">Kisht</p>
        <h1 className="mt-1 text-xl font-semibold">{t("loginTitle")}</h1>
        <p className="text-sm text-muted">{t("loginSubtitle")}</p>
      </div>

      <form onSubmit={submit} className="card flex flex-col gap-4 p-5">
        <label className="flex flex-col gap-1 text-sm font-medium">
          {t("email")}
          <input
            type="email" required autoComplete="username" inputMode="email" value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="min-h-12 rounded-xl border border-line px-3 text-base font-normal"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          {t("password")}
          <div className="flex rounded-xl border border-line">
            <input
              type={showPassword ? "text" : "password"} required autoComplete="current-password" value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="min-h-12 min-w-0 flex-1 rounded-xl px-3 text-base font-normal outline-none"
            />
            <button
              type="button" onClick={() => setShowPassword(!showPassword)}
              className="min-h-12 min-w-16 px-3 text-sm text-accent"
            >
              {showPassword ? t("hide") : t("show")}
            </button>
          </div>
        </label>

        {error && <p role="alert" className="rounded-xl bg-red-bg p-3 text-sm text-red">{error}</p>}

        <button type="submit" disabled={busy} className="min-h-12 rounded-xl bg-accent font-medium text-white disabled:opacity-60">
          {busy ? t("signingIn") : t("signIn")}
        </button>
        <p className="text-sm text-muted">{t("forgot")}</p>
      </form>

      <div className="mt-6 space-y-2 text-xs text-muted">
        <p>{t("firstLoginNote")}</p>
        <p>{t("dpdpNote")}</p>
      </div>
    </main>
  );
}
