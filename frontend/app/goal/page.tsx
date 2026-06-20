"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Loader2, Sparkles, Globe } from "lucide-react";
import Navbar from "@/components/Navbar";
import { api } from "@/lib/api";
import { DEMO_GOALS, LANG_LABELS } from "@/lib/types";
import type { Language } from "@/lib/types";
import { cn } from "@/lib/cn";

function GoalContent() {
  const router       = useRouter();
  const params       = useSearchParams();
  const textareaRef  = useRef<HTMLTextAreaElement>(null);

  const [goal,     setGoal]     = useState("");
  const [language, setLanguage] = useState<Language>("en");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

  // Pre-fill from URL query param (e.g. from landing chips)
  useEffect(() => {
    const q = params.get("q");
    if (q) setGoal(decodeURIComponent(q));
    textareaRef.current?.focus();
  }, [params]);

  // Auto-resize textarea
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

  function pickGoal(g: string) {
    setGoal(g);
    textareaRef.current?.focus();
  }

  return (
    <div className="flex min-h-dvh flex-col bg-[--background]">
      <Navbar language={language} onLanguageChange={setLanguage} />

      <main className="flex flex-1 flex-col items-center justify-center px-4 py-16">
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-2xl"
        >
          {/* Title */}
          <div className="mb-8 text-center">
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-[--primary]/30 bg-teal-950/40 px-4 py-1.5 text-sm text-[--primary]">
              <Sparkles size={13} />
              Describe your need in plain language
            </div>
            <h1 className="text-3xl font-bold text-[--foreground] sm:text-4xl">
              What do you need help with?
            </h1>
            <p className="mt-3 text-[--muted-fg]">
              Tell us your situation. No need to know form numbers or office names.
            </p>
          </div>

          {/* Language selector */}
          <div className="mb-4 flex items-center gap-2">
            <Globe size={14} className="text-[--muted-fg]" />
            <span className="text-xs text-[--muted-fg]">Language:</span>
            <div className="flex gap-1">
              {(Object.keys(LANG_LABELS) as Language[]).map((l) => (
                <button
                  key={l}
                  onClick={() => setLanguage(l)}
                  className={cn(
                    "rounded-lg px-3 py-1 text-xs font-medium transition-colors",
                    l === language
                      ? "bg-[--primary] text-white"
                      : "border border-[--border] text-[--muted-fg] hover:border-[--primary]/50 hover:text-[--primary]",
                  )}
                >
                  {LANG_LABELS[l]}
                </button>
              ))}
            </div>
          </div>

          {/* Input form */}
          <form onSubmit={(e) => { e.preventDefault(); void handleStart(); }}>
            <div className={cn(
              "rounded-2xl border bg-[--surface] p-1 transition-all duration-300",
              goal ? "border-[--primary]/60 glow-teal" : "border-[--border]",
            )}>
              <textarea
                ref={textareaRef}
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="e.g. I lost my NIC and need to apply for a passport"
                rows={3}
                className="w-full resize-none rounded-xl bg-transparent px-4 py-4 text-base text-[--foreground] placeholder:text-[--muted-fg] focus:outline-none"
                style={{ minHeight: 100, maxHeight: 300 }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                    e.currentTarget.form?.requestSubmit();
                  }
                }}
              />
              <div className="flex items-center justify-between px-3 pb-3">
                <span className="text-xs text-[--muted-fg]">
                  {goal.length > 0 ? `${goal.length} chars` : "⌘↵ to submit"}
                </span>
                <button
                  type="submit"
                  disabled={!goal.trim() || loading}
                  className={cn(
                    "flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold text-white transition-all",
                    goal.trim() && !loading
                      ? "bg-[--primary] hover:bg-teal-500 shadow-md shadow-teal-900/40"
                      : "bg-[--muted] cursor-not-allowed text-[--muted-fg]",
                  )}
                >
                  {loading
                    ? <><Loader2 size={16} className="animate-spin" /> Starting…</>
                    : <>Start My Procedure <ArrowRight size={16} /></>
                  }
                </button>
              </div>
            </div>
          </form>

          {/* Error */}
          <AnimatePresence>
            {error && (
              <motion.p
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="mt-3 rounded-lg border border-[--danger]/30 bg-red-950/20 px-4 py-2 text-sm text-[--danger]"
              >
                {error} — is the backend running?
              </motion.p>
            )}
          </AnimatePresence>

          {/* Example goals */}
          <div className="mt-8">
            <p className="mb-3 text-xs font-medium uppercase tracking-widest text-[--muted-fg]">
              Try an example
            </p>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {DEMO_GOALS.map((g) => (
                <button
                  key={g}
                  onClick={() => pickGoal(g)}
                  className="group flex items-center gap-2 rounded-xl border border-[--border] bg-[--surface] px-4 py-3 text-left text-sm text-[--muted-fg] hover:border-[--primary]/50 hover:text-[--primary] transition-colors"
                >
                  <span className="flex-1 leading-snug">{g}</span>
                  <ArrowRight size={13} className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              ))}
            </div>
          </div>
        </motion.div>
      </main>
    </div>
  );
}

export default function GoalPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-dvh items-center justify-center bg-[--background]">
          <Loader2 size={32} className="animate-spin text-[--primary]" />
        </div>
      }
    >
      <GoalContent />
    </Suspense>
  );
}
