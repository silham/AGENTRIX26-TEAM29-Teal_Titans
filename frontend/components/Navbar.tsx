"use client";

import Link from "next/link";
import Image from "next/image";
import { Database, Globe, LogOut, User } from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { cn } from "@/lib/cn";
import type { Language } from "@/lib/types";
import { LANG_LABELS } from "@/lib/types";
import { useLanguage, useT } from "@/lib/i18n";
import { getStoredUser, isAdmin, isAuthenticated, signOut } from "@/lib/api";
import InstallPrompt from "./InstallPrompt";

/**
 * Language was previously an optional prop that only /goal passed, so the
 * picker silently did nothing on every other page. It now reads the shared
 * context, which is why this component takes no props at all.
 */
export default function Navbar() {
  const { language, setLanguage } = useLanguage();
  const t        = useT();
  const router   = useRouter();
  const [langOpen,   setLangOpen]   = useState(false);
  const [userOpen,   setUserOpen]   = useState(false);
  const [authed,     setAuthed]     = useState(false);
  const [userEmail,  setUserEmail]  = useState<string | null>(null);
  const [userName,   setUserName]   = useState<string | null>(null);
  const [admin,      setAdmin]      = useState(false);

  // Read auth state on mount (sessionStorage is client-only)
  useEffect(() => {
    setAuthed(isAuthenticated());
    const u = getStoredUser();
    if (u) { setUserEmail(u.email); setUserName(u.name); }
    setAdmin(isAdmin());
  }, []);

  function handleSignOut() {
    signOut();
    setAuthed(false);
    setUserEmail(null);
    setUserName(null);
    setAdmin(false);
    setUserOpen(false);
    router.push("/");
  }

  // Avatar initials
  const initials = userName
    ? userName.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()
    : userEmail
      ? userEmail[0].toUpperCase()
      : "?";

  return (
    <header className="sticky top-0 z-50 w-full border-b border-(--border) bg-white shadow-sm">
      <div className="mx-auto flex h-14 max-w-lg items-center justify-between px-4">

        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5">
          {/* priority: this is the LCP element on every page, and it sits in a
              sticky header, so lazy-loading it causes a visible pop-in. */}
          <Image
            src="/logo-transparent.png"
            alt={t("nav.logoAlt")}
            width={36}
            height={36}
            priority
            className="h-9 w-9 shrink-0"
          />
          <div className="leading-tight">
            <p className="text-base font-bold text-(--foreground)">{t("nav.brand")}</p>
            <p className="hidden text-[10px] text-(--muted-fg) sm:block">{t("nav.tagline")}</p>
          </div>
        </Link>

        <div className="flex items-center gap-2">

          {/* Renders nothing until the browser says the app is installable. */}
          <InstallPrompt />

          {/* Language selector */}
          <div className="relative">
            <button
              onClick={() => { setLangOpen((p) => !p); setUserOpen(false); }}
              aria-label={t("nav.language")}
              className="flex items-center gap-1.5 rounded-xl border border-(--border) bg-(--surface) px-3 py-2 text-sm font-medium text-(--foreground) hover:border-(--primary) transition-colors"
            >
              <Globe size={15} className="text-(--muted-fg)" />
              {LANG_LABELS[language]}
            </button>

            <AnimatePresence>
              {langOpen && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setLangOpen(false)} />
                  <motion.div
                    initial={{ opacity: 0, y: -4, scale: 0.97 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -4, scale: 0.97 }}
                    transition={{ duration: 0.15 }}
                    className="absolute right-0 top-12 z-20 w-40 overflow-hidden rounded-2xl border border-(--border) bg-white shadow-xl"
                  >
                    {(Object.keys(LANG_LABELS) as Language[]).map((l) => (
                      <button
                        key={l}
                        onClick={() => { setLanguage(l); setLangOpen(false); }}
                        className={cn(
                          "w-full px-4 py-3 text-left text-sm transition-colors hover:bg-(--surface)",
                          l === language ? "font-semibold text-(--primary)" : "text-(--foreground)",
                        )}
                      >
                        {LANG_LABELS[l]}
                      </button>
                    ))}
                  </motion.div>
                </>
              )}
            </AnimatePresence>
          </div>

          {/* User avatar / sign-in */}
          {authed ? (
            <div className="relative">
              <button
                onClick={() => { setUserOpen((p) => !p); setLangOpen(false); }}
                className="flex h-9 w-9 items-center justify-center rounded-xl bg-(--primary) text-sm font-bold text-white hover:opacity-90 transition-opacity"
                title={userEmail ?? undefined}
                aria-label={t("nav.account")}
              >
                {initials}
              </button>

              <AnimatePresence>
                {userOpen && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setUserOpen(false)} />
                    <motion.div
                      initial={{ opacity: 0, y: -4, scale: 0.97 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -4, scale: 0.97 }}
                      transition={{ duration: 0.15 }}
                      className="absolute right-0 top-12 z-20 w-56 overflow-hidden rounded-2xl border border-(--border) bg-white shadow-xl"
                    >
                      {/* User info */}
                      <div className="border-b border-(--border) px-4 py-3.5">
                        <div className="flex items-center gap-2.5">
                          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-(--primary) text-xs font-bold text-white">
                            {initials}
                          </div>
                          <div className="min-w-0">
                            {userName && (
                              <p className="truncate text-sm font-semibold text-(--foreground)">{userName}</p>
                            )}
                            <p className="truncate text-xs text-(--muted-fg)">{userEmail}</p>
                          </div>
                        </div>
                      </div>

                      {/* Menu items */}
                      <Link
                        href="/dashboard"
                        onClick={() => setUserOpen(false)}
                        className="flex items-center gap-2.5 px-4 py-3 text-sm text-(--foreground) hover:bg-(--surface) transition-colors"
                      >
                        <User size={15} className="text-(--muted-fg)" />
                        {t("nav.myPlans")}
                      </Link>

                      {/* Shown only to admins. Cosmetic — /admin and every
                          /admin/* API call are gated server-side by role. */}
                      {admin && (
                        <Link
                          href="/admin"
                          onClick={() => setUserOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-3 text-sm text-(--foreground) hover:bg-(--surface) transition-colors"
                        >
                          <Database size={15} className="text-(--muted-fg)" />
                          {t("nav.knowledgeBase")}
                        </Link>
                      )}

                      <button
                        onClick={handleSignOut}
                        className="flex w-full items-center gap-2.5 border-t border-(--border) px-4 py-3 text-sm text-(--danger) hover:bg-red-50 transition-colors"
                      >
                        <LogOut size={15} />
                        {t("nav.signOut")}
                      </button>
                    </motion.div>
                  </>
                )}
              </AnimatePresence>
            </div>
          ) : (
            <Link
              href="/auth"
              className="rounded-xl bg-(--primary) px-3 py-2 text-sm font-semibold text-white hover:bg-(--primary-dark) transition-colors"
            >
              {t("nav.signIn")}
            </Link>
          )}
        </div>

      </div>
    </header>
  );
}
