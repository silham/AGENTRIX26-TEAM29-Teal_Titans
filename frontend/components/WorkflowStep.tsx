"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Lock, Clock, ArrowRight, ExternalLink } from "lucide-react";
import { cn } from "@/lib/cn";
import type { Step } from "@/lib/types";

const STATUS_CONFIG = {
  completed: { icon: CheckCircle2, color: "text-[--success]",  bg: "bg-emerald-950/30", border: "border-emerald-700/40", badge: "bg-emerald-500/20 text-[--success]" },
  active:    { icon: ArrowRight,   color: "text-[--primary]",  bg: "bg-teal-950/30",    border: "border-[--primary]/60", badge: "bg-teal-500/20 text-[--primary]" },
  pending:   { icon: Clock,        color: "text-[--muted-fg]", bg: "bg-[--surface]",    border: "border-[--border]",     badge: "bg-[--muted] text-[--muted-fg]" },
  locked:    { icon: Lock,         color: "text-amber-400",    bg: "bg-amber-950/20",   border: "border-amber-700/40",   badge: "bg-amber-500/20 text-amber-400" },
  skipped:   { icon: ArrowRight,   color: "text-[--muted-fg]", bg: "bg-[--surface]",    border: "border-[--border]",     badge: "bg-[--muted] text-[--muted-fg]" },
};

interface Props {
  step: Step;
  index: number;
  isLast: boolean;
  onExplain?: (step: Step) => void;
}

export default function WorkflowStep({ step, index, isLast, onExplain }: Props) {
  const cfg = STATUS_CONFIG[step.status];
  const Icon = cfg.icon;

  return (
    <div className="flex gap-4">
      {/* Connector + icon */}
      <div className="flex flex-col items-center">
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: index * 0.06, type: "spring" }}
          className={cn(
            "flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 transition-colors",
            cfg.bg, cfg.border,
          )}
        >
          <Icon size={16} className={cfg.color} />
        </motion.div>
        {!isLast && (
          <div className={cn(
            "w-0.5 flex-1 mt-1 transition-colors duration-700",
            step.status === "completed" ? "bg-emerald-700/40" : "bg-[--border]",
          )} />
        )}
      </div>

      {/* Content */}
      <motion.div
        initial={{ x: 12, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ delay: index * 0.06 + 0.04 }}
        className={cn(
          "mb-4 flex-1 rounded-xl border p-4 transition-colors",
          cfg.bg, cfg.border,
          step.status === "locked" && "opacity-75",
        )}
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[10px] font-medium text-[--muted-fg]">Step {index + 1}</span>
              <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide", cfg.badge)}>
                {step.status}
              </span>
            </div>
            <p className={cn("mt-1 font-medium text-sm sm:text-base", cfg.color)}>{step.title}</p>
            {step.description && (
              <p className="mt-1 text-xs text-[--muted-fg] leading-relaxed">{step.description}</p>
            )}
            {step.status === "locked" && step.reason && (
              <p className="mt-2 flex items-center gap-1.5 text-xs text-amber-400/80">
                <Lock size={11} />
                {step.reason}
              </p>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {step.source_url && (
              <a
                href={step.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 rounded-lg border border-[--border] px-2 py-1 text-[10px] text-[--muted-fg] hover:text-[--primary] hover:border-[--primary] transition-colors"
              >
                <ExternalLink size={10} />
                Source
              </a>
            )}
            {onExplain && (
              <button
                onClick={() => onExplain(step)}
                className="rounded-lg border border-[--border] px-2 py-1 text-[10px] text-[--muted-fg] hover:text-[--primary] hover:border-[--primary] transition-colors"
              >
                Why?
              </button>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
}
