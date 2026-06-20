"use client";

import { motion } from "framer-motion";
import { CheckCircle2, XCircle, AlertCircle, Upload, FileQuestion } from "lucide-react";
import { cn } from "@/lib/cn";
import type { Document } from "@/lib/types";

const DOC_CFG = {
  accepted: {
    Icon: CheckCircle2,
    iconClass: "text-(--success)",
    cardClass: "border-green-200 bg-(--success-light)",
    badge: "Ready ✓",
    badgeClass: "bg-green-100 text-(--success)",
  },
  rejected: {
    Icon: XCircle,
    iconClass: "text-(--danger)",
    cardClass: "border-red-200 bg-(--danger-light)",
    badge: "Problem — see below",
    badgeClass: "bg-red-100 text-(--danger)",
  },
  incomplete: {
    Icon: AlertCircle,
    iconClass: "text-orange-500",
    cardClass: "border-orange-200 bg-orange-50",
    badge: "Not complete",
    badgeClass: "bg-orange-100 text-orange-700",
  },
  missing: {
    Icon: FileQuestion,
    iconClass: "text-(--muted-fg)",
    cardClass: "border-(--border) bg-white",
    badge: "You need this",
    badgeClass: "bg-(--surface) text-(--muted-fg)",
  },
  needs_verification: {
    Icon: Upload,
    iconClass: "text-(--primary)",
    cardClass: "border-blue-200 bg-(--primary-light)",
    badge: "Being checked",
    badgeClass: "bg-blue-100 text-(--primary)",
  },
};

interface Props {
  documents: Document[];
  onUpload?: (name: string) => void;
}

export default function DocumentChecklist({ documents, onUpload }: Props) {
  if (!documents.length) return null;

  return (
    <div className="space-y-3">
      {documents.map((doc, i) => {
        const cfg      = DOC_CFG[doc.status];
        const Icon     = cfg.Icon;
        const canUpload =
          (doc.status === "missing" || doc.status === "needs_verification") && onUpload;

        return (
          <motion.div
            key={doc.id}
            initial={{ y: 8, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: i * 0.06 }}
            className={cn("rounded-2xl border p-4 transition-colors", cfg.cardClass)}
          >
            <div className="flex items-start gap-3">
              <Icon size={22} className={cn("mt-0.5 shrink-0", cfg.iconClass)} />
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <p className="text-base font-semibold text-(--foreground)">{doc.name}</p>
                  <span className={cn("shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold", cfg.badgeClass)}>
                    {cfg.badge}
                  </span>
                </div>
                {doc.issues.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {doc.issues.map((issue, j) => (
                      <li key={j} className="text-sm text-(--danger)">• {issue}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {canUpload && (
              <button
                onClick={() => onUpload(doc.name)}
                className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed border-(--primary) bg-white py-3 text-sm font-semibold text-(--primary) hover:bg-(--primary-light) active:scale-95 transition-all"
              >
                <Upload size={16} />
                Upload this document
              </button>
            )}
          </motion.div>
        );
      })}
    </div>
  );
}

