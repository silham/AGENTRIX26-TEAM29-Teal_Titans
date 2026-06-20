"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, ChevronLeft, Loader2, X } from "lucide-react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import { api } from "@/lib/api";
import { DEMO_GOALS, LANG_LABELS } from "@/lib/types";
import type { Language } from "@/lib/types";
import { cn } from "@/lib/cn";

function GoalContent() {
  const router      = useRouter();
  const params      = useSearchParams();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [goal,     setGoal]     = useState("");
  const [language, setLanguage] = useState<Language>("en");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

  useEffect(() => {
    const q = params.get("q");
    if (q) setGoal(decodeURIComponent(q));
    textareaRef.current?.focus();
  }, [params]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [goal]);

  async function ensureToken() {
    if (!sessionStorage.getItem("helplk_token")) {
      const res  = await fetch("/api/demo-token", { method: "POST" });
      const data = await res.json() as { token: string };
      sessionStorage.setItem("helplk_token", data.token);
    }
  }

  async function handleStart() {
    if (!goal.trim()) return;
    setLoading(true);
    setError("");
    try {
      await ensureToken();
      const case_ = await api.createCase(goal.trim(), language);
      router.push(`/cases/${case_.id}/processing`);
    } catch (err) {
      setError(String(err));
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-dvh flex-col bg-(--background)">
      <Navbar language={language} onLanguageChange={setLanguage} />

      <main className="flex-1 px-4 pb-10 pt-5">
        <div className="mx-auto w-full max-w-lg space-y-4">

          {/* Back link */}
          <Link
            href="/"
            className="inline-flex items-center gap-1 text-sm font-semibold text-(--muted-fg) hover:text-(--primary) transition-colors"
          >
            <ChevronLeft size={16} /> Back to Home
          </Link>

          {/* Heading */}
          <motion.div initial={{ y: 10, opacity: 0 }} animate={{ y: 0, opacity: 1 }}>
            <h1 className="text-2xl font-extrabold text-(--foreground)">
              What do you need help with?
            </h1>
            <p className="mt-1.5 text-sm leading-relaxed text-(--muted-fg)">
              Type in your own words. No need to know form names or office addresses.
            </p>
          </motion.div>

          {/* Language selector */}
          <div className="flex flex-wrap items-center gap-2">
            {(Object.keys(LANG_LABELS) as Language[]).map((l) => (
              <button
                key={l}
                onClick={() => setLanguage(l)}
                className={cn(
                  "rounded-xl px-4 py-2 text-sm font-semibold transition-colors",
                  l === language
                    ? "bg-(--primary) text-white shadow-sm"
                    : "border border-(--border) bg-white text-(--foreground) hover:border-(--primary)",
                )}
              >
                {LANG_LABELS[l]}
              </button>
            ))}
          </div>

          {/* Input card */}
          <motion.div
            initial={{ y: 10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.08 }}
            className="overflow-hidden rounded-2xl bg-white shadow-sm"
          >
            <div className={cn("border-2 rounded-2xl transition-all", goal ? "border-(--primary)" : "border-white")}>
              <textarea
                ref={textareaRef}
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="e.g. I lost my ID card and need to apply for a passport"
                rows={4}
                className="w-full resize-none bg-transparent px-4 pb-2 pt-4 text-base leading-relaxed text-(--foreground) placeholder:text-(--muted-fg) focus:outline-none"
                style={{ minHeight: 120 }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void handleStart();
                }}
              />

              {/* Toolbar row */}
              <div className="flex items-center justify-between border-t border-(--border) px-4 py-3">
                {goal ? (
                  <button
                    onClick={() => { setGoal(""); textareaRef.current?.focus(); }}
                    className="flex items-center gap-1 text-xs text-(--muted-fg) hover:text-(--danger) transition-colors"
                  >
                    <X size={13} /> Clear
                  </button>
                ) : (
                  <span className="text-xs text-(--muted-fg)">Write your question above</span>
                )}
                <button
                  onClick={() => void handleStart()}
                  disabled={!goal.trim() || loading}
                  className={cn(
                    "flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-bold text-white transition-all active:scale-95",
                    goal.trim() && !loading
                      ? "bg-(--primary) hover:bg-(--primary-dark)"
                      : "cursor-not-allowed bg-(--border) text-(--muted-fg)",
                  )}
                >
                  {loading ? (
                    <><Loader2 size={15} className="animate-spin" /> Please wait…</>
                  ) : (
                    <>Get My Steps <ArrowRight size={15} /></>
                  )}
                </button>
              </div>
            </div>
          </motion.div>

          {/* Full-width submit (mobile friendly large tap target) */}
          {goal.trim() && !loading && (
            <motion.button
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              onClick={() => void handleStart()}
              className="flex w-full items-center justify-center gap-2 rounded-2xl bg-(--primary) py-4 text-base font-bold text-white shadow-md hover:bg-(--primary-dark) active:scale-[0.98] transition-all"
            >
              Get My Steps <ArrowRight size={18} />
            </motion.button>
          )}

          {/* Error */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="rounded-xl border border-red-200 bg-(--danger-light) px-4 py-3 text-sm text-(--danger)"
              >
                Something went wrong. Please check that the server is running and try again.
              </motion.div>
            )}
          </AnimatePresence>

          {/* Example goals */}
          <div>
            <p className="mb-2.5 text-sm font-semibold text-(--muted-fg)">
              Or choose a common question:
            </p>
            <div className="overflow-hidden rounded-2xl bg-white shadow-sm">
              {DEMO_GOALS.map((g, i) => (
                <motion.button
                  key={g}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.05 + i * 0.05 }}
                  onClick={() => { setGoal(g); textareaRef.current?.focus(); }}
                  className={cn(
                    "flex w-full items-center justify-between px-4 py-3.5 text-left transition-colors hover:bg-(--background) active:bg-(--background)",
                    i < DEMO_GOALS.length - 1 ? "border-b border-(--border)" : "",
                  )}
                >
                  <span className="text-sm leading-snug text-(--foreground)">{g}</span>
                  <ArrowRight size={15} className="ml-3 shrink-0 text-(--muted-fg)" />
                </motion.button>
              ))}
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}

export default function GoalPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-dvh items-center justify-center bg-(--background)">
          <Loader2 size={32} className="animate-spin text-(--primary)" />
        </div>
      }
    >
      <GoalContent />
    </Suspense>
  );
}
