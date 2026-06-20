"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Trash2, Clock } from "lucide-react";
import { cn } from "@/lib/cn";
import type { Case } from "@/lib/types";

interface Props {
  case_: Case;
  index: number;
  onDelete?: (id: string) => void;
}

export default function CaseCard({ case_: c, index, onDelete }: Props) {
  const date = new Date(c.updated_at).toLocaleDateString("en-GB", {
    day: "numeric", month: "short", year: "numeric",
  });

  const nextStep = c.steps.find((s) => s.status === "active" || s.status === "pending");

  return (
    <motion.div
      initial={{ y: 16, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ delay: index * 0.07 }}
      className="group relative rounded-2xl border border-[--border] bg-[--surface] p-5 hover:border-[--primary]/60 transition-colors overflow-hidden"
    >
      {/* Progress bar strip */}
      <div className="absolute top-0 left-0 h-0.5 w-full bg-[--border]">
        <motion.div
          className="h-full bg-gradient-to-r from-[--primary] to-emerald-400"
          initial={{ width: 0 }}
          animate={{ width: `${c.progress}%` }}
          transition={{ delay: index * 0.07 + 0.3, duration: 0.8, ease: "easeOut" }}
        />
      </div>

      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-[--foreground] line-clamp-2 leading-snug">
            {c.goal}
          </p>

          <div className="mt-2 flex flex-wrap items-center gap-3">
            <span className={cn(
              "rounded-full px-2.5 py-0.5 text-[11px] font-medium",
              c.status === "completed" ? "bg-emerald-500/20 text-[--success]" : "bg-teal-500/15 text-[--primary]",
            )}>
              {c.progress}% complete
            </span>
            <span className="flex items-center gap-1 text-[11px] text-[--muted-fg]">
              <Clock size={11} />
              {date}
            </span>
          </div>

          {nextStep && (
            <p className="mt-2.5 text-xs text-[--muted-fg] line-clamp-1">
              Next: <span className="text-[--foreground]">{nextStep.title}</span>
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 shrink-0">
          {onDelete && (
            <button
              onClick={(e) => { e.preventDefault(); onDelete(c.id); }}
              className="opacity-0 group-hover:opacity-100 rounded-lg p-2 text-[--muted-fg] hover:text-[--danger] hover:bg-red-950/30 transition-all"
              title="Delete case"
            >
              <Trash2 size={14} />
            </button>
          )}
          <Link
            href={`/cases/${c.id}`}
            className="flex items-center gap-1.5 rounded-lg bg-[--primary]/15 px-3 py-2 text-xs font-medium text-[--primary] hover:bg-[--primary]/25 transition-colors"
          >
            Continue
            <ArrowRight size={13} />
          </Link>
        </div>
      </div>
    </motion.div>
  );
}
