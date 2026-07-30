"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, ChevronLeft, Loader2, X } from "lucide-react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import VoiceInputButton from "@/components/VoiceInputButton";
import { ApiError, AuthError, api, isAuthenticated } from "@/lib/api";
import { isLanguage, useLanguage, useT } from "@/lib/i18n";
import { cn } from "@/lib/cn";

const EXAMPLE_KEYS = [
  "goal.example1", "goal.example2", "goal.example3",
  "goal.example4", "goal.example5", "goal.example6",
];

function GoalContent() {
  const router      = useRouter();
  const params      = useSearchParams();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const t           = useT();
  const { language, setLanguage } = useLanguage();

  const [goal,     setGoal]     = useState("");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

  // Restore pending goal saved before auth redirect, then apply URL param.
  // No pending-language handling: language is now a durable preference in
  // localStorage, so it already survives the auth round trip.
  useEffect(() => {
    const pending = sessionStorage.getItem("helplk_pending_goal");
    if (pending) {
      setGoal(pending);
      sessionStorage.removeItem("helplk_pending_goal");
    }

    // URL ?q= param takes priority (service shortcuts from landing page)
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

  async function handleStart() {
    if (!goal.trim()) return;

    // Gate on authentication: save goal and send to auth page
    if (!isAuthenticated()) {
      sessionStorage.setItem("helplk_pending_goal", goal.trim());
      router.push("/auth?next=/goal");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const case_ = await api.createCase(goal.trim(), language);

      // The backend detects the language actually written — which may differ
      // from the picker if the citizen typed Sinhala or Singlish while it said
      // English. What they wrote wins: the picker is a default, not a
      // commitment, and most citizens never open it.
      if (isLanguage(case_.language) && case_.language !== language) {
        setLanguage(case_.language);
      }

      router.push(`/cases/${case_.id}/processing`);
    } catch (err) {
      if (err instanceof AuthError) {
        // Token was stale — save goal and go to auth
        sessionStorage.setItem("helplk_pending_goal", goal.trim());
        router.push("/auth?next=/goal");
        return;
      }
      // 422 here is the scope guardrail refusing an off-topic goal; its
      // `detail` is a citizen-facing message (already localized server-side),
      // so show it verbatim instead of the generic fallback.
      setError(
        err instanceof ApiError && err.status === 422 && typeof err.detail === "string"
          ? err.detail
          : t("goal.error"),
      );
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-dvh flex-col bg-(--background)">
      <Navbar />

      <main className="flex-1 px-4 pb-10 pt-5">
        <div className="mx-auto w-full max-w-lg space-y-4">

          {/* Back link */}
          <Link
            href="/"
            className="inline-flex items-center gap-1 text-sm font-semibold text-(--muted-fg) hover:text-(--primary) transition-colors"
          >
            <ChevronLeft size={16} /> {t("goal.back")}
          </Link>

          {/* Heading */}
          <motion.div initial={{ y: 10, opacity: 0 }} animate={{ y: 0, opacity: 1 }}>
            <h1 className="text-2xl font-extrabold text-(--foreground)">
              {t("goal.heading")}
            </h1>
            <p className="mt-1.5 text-sm leading-relaxed text-(--muted-fg)">
              {t("goal.subtitle")}
            </p>
          </motion.div>

          {/* The page-level language picker that used to sit here is gone: the
              Navbar picker is now wired to the shared context and works on
              every page, so this was a second control for the same state. */}

          {/* Floating input bar */}
          <motion.div
            initial={{ y: 10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.08 }}
            className="rounded-2xl bg-white shadow-md flex items-end gap-3 p-4"
          >
            <textarea
              ref={textareaRef}
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder={t("goal.placeholder")}
              rows={3}
              className="flex-1 resize-none bg-transparent py-1 pl-1 text-base leading-relaxed text-(--foreground) placeholder:text-(--muted-fg) focus:outline-none focus-visible:outline-none focus:ring-0"
              style={{ minHeight: 80, maxHeight: 200, outline: "none", boxShadow: "none" }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void handleStart();
              }}
            />

            {/* Voice input: native Web Speech API where available, otherwise
                records and sends to Gemini transcription — see
                components/VoiceInputButton.tsx for why both paths exist. */}
            <VoiceInputButton
              className="mb-0.5"
              onTranscript={(text, detectedLanguage) => {
                setGoal((g) => (g ? `${g} ${text}`.trim() : text));
                if (detectedLanguage && detectedLanguage !== language) {
                  setLanguage(detectedLanguage);
                }
                textareaRef.current?.focus();
              }}
            />

            {/* Clear (only when text exists) */}
            {goal && (
              <button
                onClick={() => { setGoal(""); textareaRef.current?.focus(); }}
                className="mb-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-(--muted-fg) hover:bg-(--background) hover:text-(--danger) transition-colors"
                title={t("goal.clear")}
                aria-label={t("goal.clear")}
              >
                <X size={17} />
              </button>
            )}

            {/* Submit arrow button */}
            <button
              onClick={() => void handleStart()}
              disabled={!goal.trim() || loading}
              aria-label={t("goal.submit")}
              className={cn(
                "mb-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-all active:scale-90",
                goal.trim() && !loading
                  ? "bg-(--primary) text-white shadow-sm hover:bg-(--primary-dark)"
                  : "bg-(--border) text-(--muted-fg) cursor-not-allowed",
              )}
            >
              {loading
                ? <Loader2 size={18} className="animate-spin" />
                : <ArrowRight size={18} />}
            </button>
          </motion.div>

          <p className="px-1 text-xs text-(--muted-fg)">{t("goal.hint")}</p>

          {/* Error */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="rounded-xl border border-red-200 bg-(--danger-light) px-4 py-3 text-sm text-(--danger)"
              >
                {error}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Example goals */}
          <div>
            <p className="mb-2.5 text-sm font-semibold text-(--muted-fg)">
              {t("goal.examplesTitle")}
            </p>
            <div className="overflow-hidden rounded-2xl bg-white shadow-sm">
              {EXAMPLE_KEYS.map((key, i) => {
                const example = t(key);
                return (
                  <motion.button
                    key={key}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.05 + i * 0.05 }}
                    onClick={() => { setGoal(example); textareaRef.current?.focus(); }}
                    className={cn(
                      "flex w-full items-center justify-between px-4 py-3.5 text-left transition-colors hover:bg-(--background) active:bg-(--background)",
                      i < EXAMPLE_KEYS.length - 1 ? "border-b border-(--border)" : "",
                    )}
                  >
                    <span className="text-sm leading-snug text-(--foreground)">{example}</span>
                    <ArrowRight size={15} className="ml-3 shrink-0 text-(--muted-fg)" />
                  </motion.button>
                );
              })}
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
