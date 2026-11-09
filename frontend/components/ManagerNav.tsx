"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { LangToggle } from "@/components/LangToggle";
import { api } from "@/lib/api";
import { useLang } from "@/lib/i18n";

const LINKS = [
  { href: "/manager", label: "navDashboard" },
  { href: "/manager/import", label: "navImport" },
] as const;

export function ManagerNav() {
  const { t } = useLang();
  const path = usePathname();
  const router = useRouter();

  async function signOut() {
    await api("/auth/logout", { method: "POST" }).catch(() => undefined);
    router.replace("/manager/login");
  }

  return (
    <header className="border-b border-line bg-card">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-2 px-4 py-2">
        <span className="mr-4 text-lg font-semibold text-accent">Kisht</span>
        <nav className="flex flex-1 gap-1">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              aria-current={path === link.href ? "page" : undefined}
              className={`flex min-h-12 items-center rounded-xl px-3 text-sm font-medium ${
                path === link.href ? "bg-accent/10 text-accent" : "text-muted"
              }`}
            >
              {t(link.label)}
            </Link>
          ))}
        </nav>
        <LangToggle />
        <button type="button" onClick={signOut} className="min-h-12 px-3 text-sm text-muted">
          {t("signOut")}
        </button>
      </div>
    </header>
  );
}
