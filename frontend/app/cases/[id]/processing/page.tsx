"use client";

import { useEffect, useRef, useState, use, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Loader2, CheckCircle2, AlertCircle, HelpCircle } from "lucide-react";
import { motion } from "framer-motion";
import Navbar from "@/components/Navbar";
import { api } from "@/lib/api";
import { AGENTS } from "@/lib/types";
import type { RunEvent, QuestionField } from "@/lib/types";
import { cn } from "@/lib/cn";

// Plain-English messages — no "Agent" names shown to citizens
const STEP_MSGS: Record<string, string> = {
  planner:         "Reading what you need...",
  knowledge:       "Checking official government rules...",
  dependency:      "Finding the right steps for you...",
  run_eligibility: "Checking if you qualify...",
  run_checklist:   "Creating your personal plan...",
  document:        "Listing the documents you need...",
  form:            "Checking what forms to fill...",
  reminder:        "Almost done — finalising your plan...",
};

export default function ProcessingPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router  = useRouter();

  const [doneCount,  setDoneCount]  = useState(0);
  const [currentMsg, setCurrentMsg] = useState("Getting started...");
  const [goal,       setGoal]       = useState("");
  const [done,       setDone]       = useState(false);
  const [error,      setError]      = useState("");
  const [questions,  setQuestions]  = useState<QuestionField[] | null>(null);
  const [answers,    setAnswers]    = useState<Record<string, string | number | boolean>>({});

  const pausedRef = useRef(false);       // suppress onDone navigation while paused
  const stopRef   = useRef<(() => void) | null>(null);

  const total = AGENTS.length;
  const pct   = Math.min(100, Math.round((doneCount / total) * 100));

  useEffect(() => {
    api.getCase(id).then((c) => setGoal(c.goal)).catch(() => {});
  }, [id]);

  const startRun = useCallback((resume: boolean, ans?: Record<string, unknown>) => {
    stopRef.current?.();
    stopRef.current = api.streamRun(
      id,
      (evt: RunEvent) => {
        if (evt.status === "started" && STEP_MSGS[evt.agent]) {
          setCurrentMsg(STEP_MSGS[evt.agent]);
        }
        if (evt.status === "completed" && evt.agent !== "system") {
          setDoneCount((n) => n + 1);
        }
        if (evt.agent === "system" && evt.status === "paused") {
          pausedRef.current = true;
          setQuestions((evt.payload?.question_fields as QuestionField[]) ?? []);
          setCurrentMsg("We need a few details from you");
        }
      },
      () => {
        if (pausedRef.current) return; // stream ended because we're awaiting answers
        setDone(true);
        setCurrentMsg("Your plan is ready!");
        setTimeout(() => router.push(`/cases/${id}`), 2000);
      },
      (msg) => setError(msg),
      resume,
      ans,
    );
  }, [id, router]);

  useEffect(() => {
    startRun(false);
    return () => stopRef.current?.();
  }, [startRun]);

  function submitAnswers() {
    if (!questions) return;
    pausedRef.current = false;
    setQuestions(null);
    setCurrentMsg("Checking if you qualify...");
    startRun(true, answers);
  }

  const allAnswered =
    questions !== null &&
    questions.every((q) => answers[q.field] !== undefined && answers[q.field] !== "");

  return (
    <div className="flex min-h-dvh flex-col bg-(--background)">
      <Navbar />

      <main className="flex flex-1 flex-col items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm text-center">

          {/* Goal text */}
          {goal && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mb-8 text-sm italic leading-relaxed text-(--muted-fg) line-clamp-2"
            >
              &ldquo;{goal}&rdquo;
            </motion.p>
          )}

          {/* Status icon */}
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="mb-6 flex justify-center"
          >
            {done ? (
              <div className="flex h-24 w-24 items-center justify-center rounded-full border-4 border-green-300 bg-(--success-light)">
                <CheckCircle2 size={44} className="text-(--success)" />
              </div>
            ) : error ? (
              <div className="flex h-24 w-24 items-center justify-center rounded-full border-4 border-red-300 bg-(--danger-light)">
                <AlertCircle size={44} className="text-(--danger)" />
              </div>
            ) : questions ? (
              <div className="flex h-24 w-24 items-center justify-center rounded-full border-4 border-blue-300 bg-(--primary-light)">
                <HelpCircle size={44} className="text-(--primary)" />
              </div>
            ) : (
              <div className="flex h-24 w-24 items-center justify-center rounded-full border-4 border-blue-300 bg-(--primary-light)">
                <Loader2 size={44} className="animate-spin text-(--primary)" />
              </div>
            )}
          </motion.div>

          {/* Current message */}
          <motion.h1
            key={currentMsg}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
              "text-xl font-bold",
              done  ? "text-(--success)"  :
              error ? "text-(--danger)"   :
              "text-(--foreground)",
            )}
          >
            {done  ? "Your plan is ready!" :
             error ? "Something went wrong" :
             currentMsg}
          </motion.h1>

          {!done && !error && !questions && (
            <p className="mt-2 text-sm text-(--muted-fg)">
              Please wait — this takes about 10–20 seconds
            </p>
          )}

          {/* Eligibility questions */}
          {questions && !done && !error && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-8 space-y-5 rounded-2xl border border-(--border) bg-white p-5 text-left shadow-sm"
            >
              <p className="text-sm text-(--muted-fg)">
                Answer these so we can check you qualify before building your plan:
              </p>

              {questions.map((q) => (
                <div key={q.field}>
                  <p className="mb-2 text-sm font-semibold text-(--foreground)">{q.question}</p>

                  {q.type === "choice" && (
                    <div className="flex flex-wrap gap-2">
                      {(q.options ?? []).map((opt) => (
                        <button
                          key={String(opt.value)}
                          onClick={() => setAnswers((a) => ({ ...a, [q.field]: opt.value }))}
                          className={cn(
                            "rounded-xl border px-4 py-2 text-sm font-medium transition-colors",
                            answers[q.field] === opt.value
                              ? "border-(--primary) bg-(--primary-light) text-(--primary)"
                              : "border-(--border) bg-white text-(--foreground) hover:border-(--primary)",
                          )}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  )}

                  {q.type === "boolean" && (
                    <div className="flex gap-2">
                      {[{ v: true, l: "Yes" }, { v: false, l: "No" }].map(({ v, l }) => (
                        <button
                          key={l}
                          onClick={() => setAnswers((a) => ({ ...a, [q.field]: v }))}
                          className={cn(
                            "rounded-xl border px-5 py-2 text-sm font-medium transition-colors",
                            answers[q.field] === v
                              ? "border-(--primary) bg-(--primary-light) text-(--primary)"
                              : "border-(--border) bg-white text-(--foreground) hover:border-(--primary)",
                          )}
                        >
                          {l}
                        </button>
                      ))}
                    </div>
                  )}

                  {(q.type === "number" || q.type === "text") && (
                    <input
                      type={q.type}
                      value={String(answers[q.field] ?? "")}
                      onChange={(e) =>
                        setAnswers((a) => ({
                          ...a,
                          [q.field]: q.type === "number" && e.target.value !== ""
                            ? Number(e.target.value)
                            : e.target.value,
                        }))
                      }
                      className="w-full rounded-xl border border-(--border) px-4 py-2.5 text-sm outline-none focus:border-(--primary)"
                      placeholder={q.type === "number" ? "Enter a number" : "Type your answer"}
                    />
                  )}
                </div>
              ))}

              <button
                onClick={submitAnswers}
                disabled={!allAnswered}
                className="w-full rounded-xl bg-(--primary) py-3 text-sm font-bold text-white hover:bg-(--primary-dark) active:scale-95 transition-all disabled:opacity-50"
              >
                Continue →
              </button>
            </motion.div>
          )}

          {/* Progress bar */}
          {!done && !error && !questions && (
            <div className="mt-8">
              <div className="mb-2 flex items-center justify-between text-sm">
                <span className="text-(--muted-fg)">Progress</span>
                <span className="font-bold text-(--primary)">{pct}%</span>
              </div>
              <div className="h-3 w-full overflow-hidden rounded-full bg-(--surface)">
                <motion.div
                  className="h-full rounded-full bg-(--primary)"
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ ease: "easeOut", duration: 0.4 }}
                />
              </div>
              <p className="mt-2 text-xs text-(--muted-fg)">
                Step {doneCount} of {total}
              </p>
            </div>
          )}

          {/* Done */}
          {done && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="mt-8"
            >
              <p className="mb-4 text-sm text-(--muted-fg)">Taking you to your plan now…</p>
              <button
                onClick={() => router.push(`/cases/${id}`)}
                className="inline-flex items-center gap-2 rounded-2xl bg-(--primary) px-8 py-4 text-base font-bold text-white hover:bg-(--primary-dark) active:scale-95 transition-all"
              >
                See My Plan →
              </button>
            </motion.div>
          )}

          {/* Error */}
          {error && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-8 space-y-3">
              <p className="text-sm text-(--muted-fg)">
                Could not connect to server. Check your connection and try again.
              </p>
              <button
                onClick={() => router.push(`/cases/${id}`)}
                className="inline-flex items-center gap-2 rounded-2xl bg-(--primary) px-8 py-4 text-base font-bold text-white"
              >
                Continue Anyway →
              </button>
            </motion.div>
          )}

        </div>
      </main>
    </div>
  );
}
