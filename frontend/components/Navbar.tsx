"use client";

import Link from "next/link";
import { Globe, LogOut, User } from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { cn } from "@/lib/cn";
import type { Language } from "@/lib/types";
import { LANG_LABELS } from "@/lib/types";
import { getStoredUser, isAuthenticated, signOut } from "@/lib/api";

interface NavbarProps {
  language?: Language;
  onLanguageChange?: (l: Language) => void;
}

export default function Navbar({ language = "en", onLanguageChange }: NavbarProps) {
  const router   = useRouter();
  const [langOpen,   setLangOpen]   = useState(false);
  const [userOpen,   setUserOpen]   = useState(false);
  const [authed,     setAuthed]     = useState(false);
  const [userEmail,  setUserEmail]  = useState<string | null>(null);
  const [userName,   setUserName]   = useState<string | null>(null);

  // Read auth state on mount (sessionStorage is client-only)
  useEffect(() => {
    setAuthed(isAuthenticated());
    const u = getStoredUser();
    if (u) { setUserEmail(u.email); setUserName(u.name); }
  }, []);

  function handleSignOut() {
    signOut();
    setAuthed(false);
    setUserEmail(null);
    setUserName(null);
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
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-(--primary)">
            <span className="text-sm font-bold text-white">LK</span>
          </div>
          <div className="leading-tight">
            <p className="text-base font-bold text-(--foreground)">HelpLK</p>
            <p className="hidden text-[10px] text-(--muted-fg) sm:block">Government Services</p>
          </div>
        </Link>

        <div className="flex items-center gap-2">

          {/* Language selector */}
          <div className="relative">
            <button
              onClick={() => { setLangOpen((p) => !p); setUserOpen(false); }}
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
                        onClick={() => { onLanguageChange?.(l); setLangOpen(false); }}
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
                        My Plans
                      </Link>

                      <button
                        onClick={handleSignOut}
                        className="flex w-full items-center gap-2.5 border-t border-(--border) px-4 py-3 text-sm text-(--danger) hover:bg-red-50 transition-colors"
                      >
                        <LogOut size={15} />
                        Sign Out
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
              Sign In
            </Link>
          )}
        </div>

      </div>
    </header>
  );
}
