"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Lock, Clock, ChevronRight, ExternalLink, Loader2, Undo2 } from "lucide-react";
import { cn } from "@/lib/cn";
import { useT } from "@/lib/i18n";
import type { Step } from "@/lib/types";

// `badge` is a dictionary key, not display text — resolved at render so a
// language switch re-labels these without remounting.
const STATUS_CFG = {
  completed: {
    circleClass: "bg-(--success-light) border-green-300",
    Icon:        CheckCircle2,
    iconColor:   "text-(--success)",
    cardClass:   "border-green-200 bg-(--success-light)",
    badge:       "step.done",
    badgeClass:  "bg-green-100 text-(--success)",
  },
  active: {
    circleClass: "bg-(--primary-light) border-blue-400",
    Icon:        ChevronRight,
    iconColor:   "text-(--primary)",
    cardClass:   "border-blue-300 bg-(--primary-light) shadow-sm",
    badge:       "step.active",
    badgeClass:  "bg-blue-100 text-(--primary)",
  },
  pending: {
    circleClass: "bg-(--surface) border-(--border)",
    Icon:        Clock,
    iconColor:   "text-(--muted-fg)",
    cardClass:   "border-(--border) bg-white",
    badge:       "step.pending",
    badgeClass:  "bg-(--surface) text-(--muted-fg)",
  },
  locked: {
    circleClass: "bg-orange-50 border-orange-300",
    Icon:        Lock,
    iconColor:   "text-orange-500",
    cardClass:   "border-orange-200 bg-orange-50",
    badge:       "step.locked",
    badgeClass:  "bg-orange-100 text-orange-700",
  },
  skipped: {
    circleClass: "bg-(--surface) border-(--border)",
    Icon:        Clock,
    iconColor:   "text-(--muted-fg)",
    cardClass:   "border-(--border) bg-white opacity-50",
    badge:       "step.skipped",
    badgeClass:  "bg-(--surface) text-(--muted-fg)",
  },
};

interface Props {
  step: Step;
  index: number;
  isLast: boolean;
  onExplain?: (step: Step) => void;
  onToggle?: (step: Step) => void; // mark done / undo
  busy?: boolean;                  // this step's update is in flight
}

export default function WorkflowStep({ step, index, isLast, onExplain, onToggle, busy }: Props) {
  const t    = useT();
  const cfg  = STATUS_CFG[step.status];
  const Icon = cfg.Icon;

  return (
    <div className="flex gap-3">
      {/* Circle + connector */}
      <div className="flex flex-col items-center">
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: index * 0.07, type: "spring" }}
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 transition-colors",
            cfg.circleClass,
          )}
        >
          <Icon size={18} className={cfg.iconColor} />
        </motion.div>
        {!isLast && (
          <div className="mt-1 min-h-[24px] w-0.5 flex-1 bg-(--border)" />
        )}
      </div>

      {/* Card */}
      <motion.div
        initial={{ x: 16, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ delay: index * 0.07 + 0.05 }}
        className={cn(
          "mb-3 flex-1 rounded-2xl border p-4 transition-colors",
          cfg.cardClass,
        )}
      >
        {/* Step number + badge */}
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <span className="text-xs text-(--muted-fg)">{t("step.number", { n: index + 1 })}</span>
          <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-semibold", cfg.badgeClass)}>
            {t(cfg.badge)}
          </span>
        </div>

        {/* Title */}
        <p className="text-base font-semibold leading-snug text-(--foreground)">{step.title}</p>

        {/* Description */}
        {step.description && (
          <p className="mt-1.5 text-sm leading-relaxed text-(--muted-fg)">{step.description}</p>
        )}

        {/* Locked reason (may include an eligibility blocker + alternative path) */}
        {step.status === "locked" && (
          <p className="mt-2 text-sm text-orange-700">
            ⛔ {step.reason || t("step.lockedFallback")}
          </p>
        )}

        {/* Footer */}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {onToggle && (step.status === "active" || step.status === "pending") && (
            <button
              onClick={() => onToggle(step)}
              disabled={busy}
              className="inline-flex items-center gap-1.5 rounded-lg bg-(--primary) px-3 py-1.5 text-xs font-semibold text-white hover:bg-(--primary-dark) active:scale-95 transition-all disabled:opacity-60"
            >
              {busy ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />}
              {t("step.markDone")}
            </button>
          )}
          {onToggle && step.status === "completed" && (
            <button
              onClick={() => onToggle(step)}
              disabled={busy}
              className="inline-flex items-center gap-1.5 rounded-lg border border-(--border) bg-white px-3 py-1.5 text-xs font-semibold text-(--muted-fg) hover:text-(--foreground) transition-colors disabled:opacity-60"
            >
              {busy ? <Loader2 size={13} className="animate-spin" /> : <Undo2 size={13} />}
              {t("step.undo")}
            </button>
          )}
          {step.source_url && (
            <a
              href={step.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs font-medium text-(--primary) underline"
            >
              <ExternalLink size={11} /> {t("step.officialSource")}
            </a>
          )}
          {onExplain && (
            <button
              onClick={() => onExplain(step)}
              className="rounded-lg border border-(--border) bg-white px-3 py-1.5 text-xs font-semibold text-(--foreground) hover:border-(--primary) hover:text-(--primary) transition-colors"
            >
              {t("step.moreInfo")}
            </button>
          )}
        </div>
      </motion.div>
    </div>
  );
}

