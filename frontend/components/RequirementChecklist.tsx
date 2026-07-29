"use client";

import { motion } from "framer-motion";
import {
  AlertCircle, ArrowRight, CheckCircle2, Clock, FileQuestion, HelpCircle, Loader2, Undo2, XCircle,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { useT } from "@/lib/i18n";
import type { Requirement, RequirementStatus, SubGoal } from "@/lib/types";
import { SATISFIED } from "@/lib/types";

// `badge` holds a dictionary key, resolved at render.
const REQ_CFG: Record<RequirementStatus, {
  Icon: typeof CheckCircle2;
  iconClass: string;
  cardClass: string;
  badge: string;
  badgeClass: string;
}> = {
  confirmed: {
    Icon: CheckCircle2,
    iconClass: "text-(--success)",
    cardClass: "border-green-200 bg-(--success-light)",
    badge: "requirements.confirmed",
    badgeClass: "bg-green-100 text-(--success)",
  },
  // Legacy rows from when documents were uploaded and machine-checked. Worded
  // differently on purpose — we must not imply we verified a self-declaration.
  accepted: {
    Icon: CheckCircle2,
    iconClass: "text-(--success)",
    cardClass: "border-green-200 bg-(--success-light)",
    badge: "requirements.verified",
    badgeClass: "bg-green-100 text-(--success)",
  },
  rejected: {
    Icon: XCircle,
    iconClass: "text-(--danger)",
    cardClass: "border-red-200 bg-(--danger-light)",
    badge: "requirements.rejected",
    badgeClass: "bg-red-100 text-(--danger)",
  },
  incomplete: {
    Icon: AlertCircle,
    iconClass: "text-orange-500",
    cardClass: "border-orange-200 bg-orange-50",
    badge: "requirements.incomplete",
    badgeClass: "bg-orange-100 text-orange-700",
  },
  missing: {
    Icon: FileQuestion,
    iconClass: "text-(--muted-fg)",
    cardClass: "border-(--border) bg-white",
    badge: "requirements.missing",
    badgeClass: "bg-(--surface) text-(--muted-fg)",
  },
  needs_verification: {
    Icon: Clock,
    iconClass: "text-(--primary)",
    cardClass: "border-blue-200 bg-(--primary-light)",
    badge: "requirements.checking",
    badgeClass: "bg-blue-100 text-(--primary)",
  },
};

interface Props {
  requirements: Requirement[];
  /** Existing plans spawned from these requirements, keyed by requirement. */
  subGoals?: SubGoal[];
  onHaveIt: (r: Requirement, next: "confirmed" | "missing") => void;
  onHowToGet: (r: Requirement) => void;
  busyId?: string | null;
}

export default function RequirementChecklist({
  requirements, subGoals = [], onHaveIt, onHowToGet, busyId,
}: Props) {
  const t = useT();
  if (!requirements.length) return null;

  return (
    <div className="space-y-3">
      {requirements.map((req, i) => {
        const cfg  = REQ_CFG[req.status] ?? REQ_CFG.missing;
        const Icon = cfg.Icon;
        const busy = busyId === req.id;
        const satisfied = SATISFIED.has(req.status);
        // A plan the citizen already started for this exact requirement.
        const existingPlan = subGoals.find(
          (g) => g.parent_requirement_key && g.parent_requirement_key === req.type,
        );

        return (
          <motion.div
            key={req.id}
            initial={{ y: 8, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: i * 0.06 }}
            className={cn("rounded-2xl border p-4 transition-colors", cfg.cardClass)}
          >
            <div className="flex items-start gap-3">
              <Icon size={22} className={cn("mt-0.5 shrink-0", cfg.iconClass)} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <p className="text-base font-semibold text-(--foreground)">{req.name}</p>
                  <span className={cn("shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold", cfg.badgeClass)}>
                    {t(cfg.badge)}
                  </span>
                </div>
                {req.issues.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {req.issues.map((issue, j) => (
                      <li key={j} className="text-sm text-(--danger)">• {issue}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* Self-declared items can be taken back; verified uploads cannot
                (there is no verification to restore). */}
            {req.status === "confirmed" ? (
              <button
                onClick={() => onHaveIt(req, "missing")}
                disabled={busy}
                className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-(--border) bg-white py-2.5 text-sm font-semibold text-(--muted-fg) hover:text-(--foreground) disabled:opacity-50 active:scale-95 transition-all"
              >
                {busy ? <Loader2 size={15} className="animate-spin" /> : <Undo2 size={15} />}
                {t("requirements.undo")}
              </button>
            ) : !satisfied ? (
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => onHaveIt(req, "confirmed")}
                  disabled={busy}
                  className="flex flex-1 items-center justify-center gap-2 rounded-xl border-2 border-(--success) bg-white py-3 text-sm font-bold text-(--success) hover:bg-(--success-light) disabled:opacity-50 active:scale-95 transition-all"
                >
                  {busy ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle2 size={16} />}
                  {t("requirements.haveIt")}
                </button>

                {existingPlan ? (
                  <button
                    onClick={() => onHowToGet(req)}
                    disabled={busy}
                    className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-(--primary) bg-white py-3 text-sm font-semibold text-(--primary) hover:bg-(--primary-light) disabled:opacity-50 active:scale-95 transition-all"
                  >
                    {t("requirements.openPlan")}
                    <span className="text-xs font-normal text-(--muted-fg)">
                      {existingPlan.progress}%
                    </span>
                    <ArrowRight size={15} />
                  </button>
                ) : (
                  <button
                    onClick={() => onHowToGet(req)}
                    disabled={busy}
                    className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-(--border) bg-white py-3 text-sm font-semibold text-(--foreground) hover:border-(--primary) hover:text-(--primary) disabled:opacity-50 active:scale-95 transition-all"
                  >
                    <HelpCircle size={16} />
                    {t("requirements.howToGet")}
                  </button>
                )}
              </div>
            ) : null}
          </motion.div>
        );
      })}
    </div>
  );
}
