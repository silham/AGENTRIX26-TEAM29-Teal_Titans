"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu, X, LayoutDashboard, Globe } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/cn";
import type { Language } from "@/lib/types";
import { LANG_LABELS } from "@/lib/types";

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
];

interface NavbarProps {
  language?: Language;
  onLanguageChange?: (l: Language) => void;
}

export default function Navbar({ language = "en", onLanguageChange }: NavbarProps) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [langOpen, setLangOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-[--border] glass">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 group">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[--primary]">
            <span className="text-sm font-bold text-white">AI</span>
          </div>
          <span className="font-bold text-[--foreground] group-hover:text-[--primary] transition-colors">
            HelpLK <span className="gradient-text">AI</span>
          </span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-6">
          {NAV_LINKS.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-1.5 text-sm transition-colors hover:text-[--primary]",
                pathname === href ? "text-[--primary]" : "text-[--muted-fg]",
              )}
            >
              <Icon size={15} />
              {label}
            </Link>
          ))}

          {/* Language selector */}
          <div className="relative">
            <button
              onClick={() => setLangOpen((p) => !p)}
              className="flex items-center gap-1.5 rounded-lg border border-[--border] px-3 py-1.5 text-sm text-[--muted-fg] hover:border-[--primary] hover:text-[--primary] transition-colors"
            >
              <Globe size={14} />
              {LANG_LABELS[language]}
            </button>
            <AnimatePresence>
              {langOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  className="absolute right-0 top-10 w-36 rounded-xl border border-[--border] bg-[--surface] shadow-2xl overflow-hidden"
                >
                  {(Object.keys(LANG_LABELS) as Language[]).map((l) => (
                    <button
                      key={l}
                      onClick={() => { onLanguageChange?.(l); setLangOpen(false); }}
                      className={cn(
                        "w-full px-4 py-2.5 text-left text-sm hover:bg-[--muted] transition-colors",
                        l === language ? "text-[--primary]" : "text-[--foreground]",
                      )}
                    >
                      {LANG_LABELS[l]}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <Link
            href="/goal"
            className="rounded-lg bg-[--primary] px-4 py-1.5 text-sm font-medium text-white hover:bg-teal-500 transition-colors"
          >
            Start Now
          </Link>
        </nav>

        {/* Mobile burger */}
        <button
          className="md:hidden text-[--muted-fg] hover:text-[--foreground] transition-colors"
          onClick={() => setOpen((p) => !p)}
          aria-label="Toggle menu"
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="md:hidden border-t border-[--border] bg-[--surface] overflow-hidden"
          >
            <div className="flex flex-col gap-1 p-4">
              {NAV_LINKS.map(({ href, label, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setOpen(false)}
                  className={cn(
                    "flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm transition-colors",
                    pathname === href
                      ? "bg-[--muted] text-[--primary]"
                      : "text-[--muted-fg] hover:bg-[--muted]",
                  )}
                >
                  <Icon size={16} />
                  {label}
                </Link>
              ))}

              <div className="mt-2 border-t border-[--border] pt-2">
                <p className="mb-2 px-3 text-xs text-[--muted-fg]">Language</p>
                {(Object.keys(LANG_LABELS) as Language[]).map((l) => (
                  <button
                    key={l}
                    onClick={() => { onLanguageChange?.(l); setOpen(false); }}
                    className={cn(
                      "w-full rounded-lg px-3 py-2 text-left text-sm transition-colors",
                      l === language ? "text-[--primary]" : "text-[--muted-fg] hover:bg-[--muted]",
                    )}
                  >
                    {LANG_LABELS[l]}
                  </button>
                ))}
              </div>

              <Link
                href="/goal"
                onClick={() => setOpen(false)}
                className="mt-2 rounded-lg bg-[--primary] px-4 py-2.5 text-center text-sm font-medium text-white"
              >
                Start Now
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
