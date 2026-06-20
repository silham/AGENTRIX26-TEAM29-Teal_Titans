"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Loader2, CheckCircle2, AlertCircle, Cpu } from "lucide-react";
import AgentCard from "@/components/AgentCard";
import Navbar from "@/components/Navbar";
import { api } from "@/lib/api";
import { AGENTS } from "@/lib/types";
import type { AgentState, RunEvent } from "@/lib/types";
import { cn } from "@/lib/cn";

function buildInitialAgents(): AgentState[] {
  return AGENTS.map((a) => ({ ...a, status: "idle" as const }));
}

export default function ProcessingPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params); // Next.js 16: params is a Promise
  const router  = useRouter();

  const [agents,    setAgents]    = useState<AgentState[]>(buildInitialAgents);
  const [done,      setDone]      = useState(false);
  const [error,     setError]     = useState("");
  const [goal,      setGoal]      = useState("");
  const [statusMsg, setStatusMsg] = useState("Initialising agents…");

  // Load the case goal for display
  useEffect(() => {
    api.getCase(id)
      .then((c) => setGoal(c.goal))
      .catch(() => {});
  }, [id]);

  // Start SSE stream
  useEffect(() => {
    setStatusMsg("Starting your case…");

    const stop = api.streamRun(
      id,
      (evt: RunEvent) => {
        setAgents((prev) =>
          prev.map((a) => {
            if (a.name !== evt.agent) return a;
            if (evt.status === "started")   return { ...a, status: "running" };
            if (evt.status === "completed") return { ...a, status: "done", payload: evt.payload ?? undefined };
            if (evt.status === "error")     return { ...a, status: "error" };
            return a;
          }),
        );
        if (evt.status === "started")
          setStatusMsg(`${evt.agent.charAt(0).toUpperCase() + evt.agent.slice(1)} Agent is running…`);
      },
      () => {
        setDone(true);
        setStatusMsg("All agents completed!");
        // Auto-navigate to case detail after 1.8s
        setTimeout(() => router.push(`/cases/${id}`), 1800);
      },
      (msg) => {
        setError(msg);
        setStatusMsg("An error occurred");
      },
    );

    return stop;
  }, [id, router]);

  const completedCount = agents.filter((a) => a.status === "done").length;
  const totalCount     = agents.length;
  const pct            = Math.round((completedCount / totalCount) * 100);

  return (
    <div className="flex min-h-dvh flex-col bg-[--background]">
      <Navbar />

      <main className="flex flex-1 flex-col items-center px-4 py-12">
        <div className="w-full max-w-xl">

          {/* Header */}
          <motion.div
            initial={{ y: -12, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="mb-10 text-center"
          >
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-[--primary]/30 bg-teal-950/40 px-4 py-1.5 text-sm text-[--primary]">
              <Cpu size={13} />
              Multi-Agent Processing
            </div>
            <h1 className="text-2xl font-bold text-[--foreground] sm:text-3xl">
              Agents are planning your procedure
            </h1>
            {goal && (
              <p className="mt-2 text-sm text-[--muted-fg] italic line-clamp-2">
                &ldquo;{goal}&rdquo;
              </p>
            )}
          </motion.div>

          {/* Progress bar */}
          <div className="mb-8">
            <div className="mb-2 flex items-center justify-between text-sm">
              <span className="flex items-center gap-2 text-[--muted-fg]">
                {done
                  ? <CheckCircle2 size={14} className="text-[--success]" />
                  : error
                  ? <AlertCircle size={14} className="text-[--danger]" />
                  : <Loader2 size={14} className="animate-spin text-[--primary]" />
                }
                {statusMsg}
              </span>
              <span className="font-mono text-xs text-[--primary]">{pct}%</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-[--border]">
              <motion.div
                className={cn(
                  "h-full rounded-full",
                  done  ? "bg-[--success]" :
                  error ? "bg-[--danger]" :
                  "bg-gradient-to-r from-[--primary] to-emerald-400",
                )}
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ ease: "easeOut", duration: 0.4 }}
              />
            </div>
          </div>

          {/* Agent cards */}
          <div>
            {agents.map((agent, i) => (
              <AgentCard
                key={agent.name}
                agent={agent}
                index={i}
                isLast={i === agents.length - 1}
              />
            ))}
          </div>

          {/* Error state */}
          {error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-4 rounded-xl border border-[--danger]/30 bg-red-950/20 p-4 text-sm text-[--danger]"
            >
              <p className="font-medium">Something went wrong</p>
              <p className="mt-1 text-xs opacity-80">{error}</p>
              <button
                onClick={() => router.push(`/cases/${id}`)}
                className="mt-3 text-xs underline hover:no-underline"
              >
                Go to case anyway →
              </button>
            </motion.div>
          )}

          {/* Done state */}
          {done && (
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              className="mt-4 rounded-xl border border-[--success]/30 bg-emerald-950/20 p-4 text-center"
            >
              <CheckCircle2 size={28} className="mx-auto mb-2 text-[--success]" />
              <p className="font-semibold text-[--success]">Your procedure plan is ready!</p>
              <p className="mt-1 text-xs text-[--muted-fg]">Redirecting to your case…</p>
            </motion.div>
          )}
        </div>
      </main>
    </div>
  );
}
