"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Trash2 } from "lucide-react";
import type { Case } from "@/lib/types";

interface Props {
  case_: Case;
  index: number;
  onDelete?: (id: string) => void;
}

export default function CaseCard({ case_: c, index, onDelete }: Props) {
  const nextStep   = (c.steps ?? []).find((s) => s.status === "active" || s.status === "pending");
  const isComplete = c.status === "completed";

  return (
    <motion.div
      initial={{ y: 16, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ delay: index * 0.07 }}
      className="rounded-2xl border border-(--border) bg-white p-4 shadow-sm"
    >
      {/* Goal */}
      <p className="text-base font-semibold leading-snug text-(--foreground) line-clamp-2">
        {c.goal}
      </p>

      {/* Progress bar */}
      <div className="mt-3">
        <div className="mb-1.5 flex items-center justify-between text-sm">
          <span className="text-(--muted-fg)">{isComplete ? "Completed" : "In Progress"}</span>
          <span className="font-bold text-(--primary)">{c.progress}%</span>
        </div>
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-(--surface)">
          <motion.div
            className={
              isComplete
                ? "h-full rounded-full bg-(--success)"
                : "h-full rounded-full bg-(--primary)"
            }
            initial={{ width: 0 }}
            animate={{ width: `${c.progress}%` }}
            transition={{ delay: index * 0.07 + 0.2, duration: 0.7, ease: "easeOut" }}
          />
        </div>
      </div>

      {/* Next step */}
      {nextStep && (
        <p className="mt-2 text-xs text-(--muted-fg)">
          Next:{" "}
          <span className="font-semibold text-(--foreground)">{nextStep.title}</span>
        </p>
      )}

      {/* Actions */}
      <div className="mt-4 flex items-center gap-2">
        <Link
          href={`/cases/${c.id}`}
          className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-(--primary) py-3 text-sm font-bold text-white hover:bg-(--primary-dark) active:scale-95 transition-all"
        >
          {isComplete ? "View" : "Continue"} <ArrowRight size={15} />
        </Link>
        {onDelete && (
          <button
            onClick={() => onDelete(c.id)}
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-(--border) text-(--muted-fg) hover:border-red-300 hover:bg-red-50 hover:text-(--danger) transition-colors"
            title="Delete this plan"
          >
            <Trash2 size={17} />
          </button>
        )}
      </div>
    </motion.div>
  );
}

