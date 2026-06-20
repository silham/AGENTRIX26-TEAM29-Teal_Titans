"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";
import Navbar from "@/components/Navbar";
import { api } from "@/lib/api";
import { AGENTS } from "@/lib/types";
import type { RunEvent } from "@/lib/types";
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

  const total = AGENTS.length;
  const pct   = Math.round((doneCount / total) * 100);

  useEffect(() => {
    api.getCase(id).then((c) => setGoal(c.goal)).catch(() => {});
  }, [id]);

  useEffect(() => {
    const stop = api.streamRun(
      id,
      (evt: RunEvent) => {
        if (evt.status === "started" && STEP_MSGS[evt.agent]) {
          setCurrentMsg(STEP_MSGS[evt.agent]);
        }
        if (evt.status === "completed") {
          setDoneCount((n) => n + 1);
        }
      },
      () => {
        setDone(true);
        setCurrentMsg("Your plan is ready!");
        setTimeout(() => router.push(`/cases/${id}`), 2000);
      },
      (msg) => {
        setError(msg);
      },
    );
    return stop;
  }, [id, router]);

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

          {!done && !error && (
            <p className="mt-2 text-sm text-(--muted-fg)">
              Please wait — this takes about 10–20 seconds
            </p>
          )}

          {/* Progress bar */}
          {!done && !error && (
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
