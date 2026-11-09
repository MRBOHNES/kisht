"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useLang } from "@/lib/i18n";
import type { StringKey } from "@/lib/strings";

// Only pages that exist get a tab
const TABS: { href: string; label: StringKey }[] = [
  { href: "/today", label: "navToday" },
  { href: "/promises", label: "navPromises" },
];

export function BottomTabs() {
  const { t } = useLang();
  const path = usePathname();
  return (
    <nav className="fixed inset-x-0 bottom-0 border-t border-line bg-card">
      <ul className="mx-auto flex w-full max-w-[420px]">
        {TABS.map((tab) => {
          const active = path === tab.href;
          return (
            <li key={tab.href} className="flex-1">
              <Link
                href={tab.href}
                aria-current={active ? "page" : undefined}
                className={`flex min-h-14 items-center justify-center text-sm font-medium ${active ? "text-accent" : "text-muted"}`}
              >
                {t(tab.label)}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
