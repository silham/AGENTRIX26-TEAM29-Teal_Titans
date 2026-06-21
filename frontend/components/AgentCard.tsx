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

export default function AgentCard({ agent, index, isLast }: Props) {
  const isActive = agent.status === "running";
  const isDone   = agent.status === "done";
  const isIdle   = agent.status === "idle";
  const isError  = agent.status === "error";

  return (
    <div className="flex items-start gap-3">
      {/* Icon + connector */}
      <div className="flex flex-col items-center pt-1">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: index * 0.08 }}
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 transition-all",
            isActive && "border-(--primary) bg-(--primary-light)",
            isDone   && "border-(--success) bg-(--success-light)",
            isIdle   && "border-(--border) bg-(--surface)",
            isError  && "border-(--danger) bg-(--danger-light)",
          )}
        >
          {isActive && <Loader2 size={14} className="animate-spin text-(--primary)" />}
          {isDone   && <CheckCircle2 size={14} className="text-(--success)" />}
          {isIdle   && <Circle size={14} className="text-(--border)" />}
          {isError  && <AlertCircle size={14} className="text-(--danger)" />}
        </motion.div>
        {!isLast && <div className="mt-1 min-h-[24px] w-0.5 flex-1 bg-(--border)" />}
      </div>

      {/* Label row */}
      <motion.div
        initial={{ x: 12, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ delay: index * 0.08 + 0.04 }}
        className={cn(
          "mb-3 flex-1 rounded-2xl border px-4 py-3 transition-all",
          isActive && "border-blue-200 bg-(--primary-light)",
          isDone   && "border-green-200 bg-(--success-light)",
          isIdle   && "border-(--border) bg-(--surface) opacity-60",
          isError  && "border-red-200 bg-(--danger-light)",
        )}
      >
        <p className={cn(
          "text-sm font-semibold",
          isActive ? "text-(--primary)"  :
          isDone   ? "text-(--success)"  :
          isError  ? "text-(--danger)"   :
          "text-(--muted-fg)",
        )}>
          {isDone   && "✓ "}
          {agent.label}
        </p>
      </motion.div>
    </div>
  );
}

