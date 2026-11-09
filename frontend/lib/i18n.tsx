"use client";

import { createContext, useContext, useSyncExternalStore } from "react";

import { strings, type Lang, type StringKey } from "./strings";

type Area = "officer" | "manager";
const DEFAULT_LANG: Record<Area, Lang> = { officer: "hi", manager: "en" };

const AreaContext = createContext<Area>("officer");
const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function storedLang(area: Area): Lang {
  const saved = window.localStorage.getItem(`kisht.lang.${area}`);
  return saved === "hi" || saved === "en" ? saved : DEFAULT_LANG[area];
}

export function LangArea({ area, children }: { area: Area; children: React.ReactNode }) {
  return <AreaContext.Provider value={area}>{children}</AreaContext.Provider>;
}

export function useLang() {
  const area = useContext(AreaContext);
  const lang = useSyncExternalStore(subscribe, () => storedLang(area), () => DEFAULT_LANG[area]);

  function setLang(next: Lang) {
    window.localStorage.setItem(`kisht.lang.${area}`, next);
    listeners.forEach((listener) => listener());
  }

  function t(key: StringKey, vars: Record<string, string | number> = {}) {
    return strings[lang][key].replace(/\{(\w+)\}/g, (_, name) => String(vars[name] ?? ""));
  }

  return { lang, setLang, t };
}
