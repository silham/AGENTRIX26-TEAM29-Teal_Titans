"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Circle, Loader2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/cn";
import type { AgentState } from "@/lib/types";

interface Props {
  agent: AgentState;
  index: number;
  isLast: boolean;
}

const STATUS_ICON = {
  idle:    <Circle size={18} className="text-[--muted-fg]" />,
  running: <Loader2 size={18} className="text-[--primary] animate-spin" />,
  done:    <CheckCircle2 size={18} className="text-[--success]" />,
  error:   <AlertCircle size={18} className="text-[--danger]" />,
};

export default function AgentCard({ agent, index, isLast }: Props) {
  const isActive = agent.status === "running";
  const isDone   = agent.status === "done";
  const isIdle   = agent.status === "idle";

  return (
    <div className="flex gap-4">
      {/* Left: icon + connector */}
      <div className="flex flex-col items-center">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: index * 0.08 }}
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 transition-all duration-500",
            isActive && "border-[--primary] glow-teal",
            isDone   && "border-[--success] bg-emerald-950/40",
            isIdle   && "border-[--border] bg-[--muted]",
            agent.status === "error" && "border-[--danger]",
          )}
        >
          {STATUS_ICON[agent.status]}
        </motion.div>
        {!isLast && (
          <div
            className={cn(
              "step-line mt-1 flex-1 transition-all duration-700",
              isDone ? "bg-[--success]" : "bg-[--border]",
            )}
          />
        )}
      </div>

      {/* Right: card */}
      <motion.div
        initial={{ x: 16, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ delay: index * 0.08 + 0.05 }}
        className={cn(
          "mb-4 flex-1 rounded-xl border p-4 transition-all duration-500",
          isActive && "border-[--primary]/60 bg-teal-950/30 glow-teal",
          isDone   && "border-emerald-800/40 bg-emerald-950/20",
          isIdle   && "border-[--border] bg-[--surface] opacity-50",
          agent.status === "error" && "border-[--danger]/40 bg-red-950/20",
        )}
      >
        <div className="flex items-center justify-between gap-2">
          <p className={cn(
            "text-sm font-semibold",
            isActive ? "text-[--primary]" : isDone ? "text-[--success]" : "text-[--muted-fg]",
          )}>
            {agent.label}
          </p>
          {isActive && (
            <span className="rounded-full bg-teal-500/20 px-2 py-0.5 text-[10px] font-medium text-[--primary] uppercase tracking-wide">
              Running
            </span>
          )}
          {isDone && (
            <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-medium text-[--success] uppercase tracking-wide">
              Done
            </span>
          )}
        </div>
        <p className="mt-1 text-xs text-[--muted-fg]">{agent.description}</p>

        {/* Show extracted services from planner payload */}
        {isDone && agent.name === "planner" && Array.isArray(agent.payload?.detected_services) && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {(agent.payload!.detected_services as string[]).map((s) => (
              <span key={s} className="rounded-full bg-[--primary]/15 px-2 py-0.5 text-[10px] text-[--primary]">
                {s.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}
