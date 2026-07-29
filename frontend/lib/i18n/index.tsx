"use client";

import {
  createContext, useCallback, useContext, useEffect, useMemo, useState,
} from "react";
import type { Language } from "@/lib/types";
import { en } from "./en";
import { si } from "./si";
import { ta } from "./ta";
import type { Dictionary } from "./en";

export const DICTIONARIES: Record<Language, Dictionary> = { en, si, ta };
export const LANGUAGES: Language[] = ["en", "si", "ta"];

const STORAGE_KEY = "helplk_lang";

export function isLanguage(v: unknown): v is Language {
  return v === "en" || v === "si" || v === "ta";
}

/**
 * The current language, readable OUTSIDE React.
 *
 * `lib/api.ts` needs this to stamp the X-Language header on every request and
 * cannot use a hook, so localStorage is the single source of truth and the
 * provider is a subscriber to it rather than the owner.
 */
export function getLanguage(): Language {
  if (typeof window === "undefined") return "en";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return isLanguage(stored) ? stored : "en";
}

/**
 * Resolution order: ?lang= → localStorage → browser preference → "en".
 *
 * The URL wins so a shared link (/goal?lang=si) opens in the sender's language
 * regardless of the recipient's stored preference.
 */
function resolveInitial(): Language {
  if (typeof window === "undefined") return "en";
  const fromUrl = new URLSearchParams(window.location.search).get("lang");
  if (isLanguage(fromUrl)) return fromUrl;

  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (isLanguage(stored)) return stored;

  const nav = window.navigator.language?.slice(0, 2).toLowerCase();
  return isLanguage(nav) ? nav : "en";
}

// ── Interpolation + plurals ───────────────────────────────────────────────

type Vars = Record<string, string | number>;

function interpolate(template: string, vars?: Vars): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (whole, name: string) =>
    name in vars ? String(vars[name]) : whole,
  );
}

function lookup(dict: Dictionary, path: string): unknown {
  return path.split(".").reduce<unknown>(
    (node, part) =>
      node && typeof node === "object" ? (node as Record<string, unknown>)[part] : undefined,
    dict,
  );
}

/**
 * Resolve a dot-path against the dictionary, falling back to English and then
 * to the key itself. A missing key renders as its own path rather than blank —
 * visible in review, but never a crash in front of a citizen.
 *
 * A key ending in a plural category is selected via Intl.PluralRules using
 * `vars.count`. Sinhala and Tamil both use only one/other, as English does.
 */
function translate(lang: Language, path: string, vars?: Vars): string {
  const dict = DICTIONARIES[lang];

  let resolved = lookup(dict, path);
  if (resolved === undefined && vars && "count" in vars) {
    const category = new Intl.PluralRules(lang).select(Number(vars.count));
    resolved = lookup(dict, `${path}_${category}`) ?? lookup(dict, `${path}_other`);
  }
  if (typeof resolved !== "string" && lang !== "en") {
    return translate("en", path, vars);
  }
  return typeof resolved === "string" ? interpolate(resolved, vars) : path;
}

// ── Context ───────────────────────────────────────────────────────────────

interface LanguageContextValue {
  language: Language;
  setLanguage: (l: Language) => void;
  t: (path: string, vars?: Vars) => string;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  // Always start at "en" so the server-rendered HTML and the first client
  // render agree. The real language is applied in the effect below; the
  // inline script in layout.tsx has already painted the correct <html lang>,
  // so there is no visible flash despite this deliberate hydration-safe start.
  const [language, setLanguageState] = useState<Language>("en");

  useEffect(() => {
    const initial = resolveInitial();
    setLanguageState(initial);
    window.localStorage.setItem(STORAGE_KEY, initial);
    document.documentElement.lang = initial;
  }, []);

  const setLanguage = useCallback((next: Language) => {
    setLanguageState(next);
    window.localStorage.setItem(STORAGE_KEY, next);
    document.documentElement.lang = next;

    // Keep the URL shareable. replaceState (not push) so the language switch
    // does not become a back-button step, and not router.replace so we avoid
    // a re-render of the whole tree for a cosmetic param. Next documents this
    // exact pattern for locale switching and syncs its router with it.
    const url = new URL(window.location.href);
    url.searchParams.set("lang", next);
    window.history.replaceState(null, "", url.toString());
  }, []);

  const value = useMemo<LanguageContextValue>(
    () => ({
      language,
      setLanguage,
      t: (path, vars) => translate(language, path, vars),
    }),
    [language, setLanguage],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

function useLanguageContext(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used inside <LanguageProvider>");
  return ctx;
}

export function useLanguage() {
  const { language, setLanguage } = useLanguageContext();
  return { language, setLanguage };
}

/** `const t = useT()` → `t("case.tabSteps")`, `t("dashboard.count", { count: 3 })`. */
export function useT() {
  return useLanguageContext().t;
}
