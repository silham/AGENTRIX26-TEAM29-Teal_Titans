"use client";

import Link from "next/link";
import { Globe } from "lucide-react";
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { cn } from "@/lib/cn";
import type { Language } from "@/lib/types";
import { LANG_LABELS } from "@/lib/types";

interface NavbarProps {
  language?: Language;
  onLanguageChange?: (l: Language) => void;
}

export default function Navbar({ language = "en", onLanguageChange }: NavbarProps) {
  const [langOpen, setLangOpen] = useState(false);

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

        {/* Language selector */}
        <div className="relative">
          <button
            onClick={() => setLangOpen((p) => !p)}
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
      </div>
    </header>
  );
}

