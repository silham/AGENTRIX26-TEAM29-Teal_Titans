"use client";

import { motion } from "framer-motion";
import { CheckCircle2, XCircle, AlertCircle, Upload, FileQuestion } from "lucide-react";
import { cn } from "@/lib/cn";
import type { Document } from "@/lib/types";

const DOC_CONFIG = {
  accepted:           { icon: CheckCircle2, color: "text-[--success]",  bg: "bg-emerald-950/30", border: "border-emerald-700/40", label: "Accepted" },
  rejected:           { icon: XCircle,      color: "text-[--danger]",   bg: "bg-red-950/20",     border: "border-red-700/40",     label: "Rejected" },
  incomplete:         { icon: AlertCircle,  color: "text-amber-400",    bg: "bg-amber-950/20",   border: "border-amber-700/40",   label: "Incomplete" },
  missing:            { icon: FileQuestion, color: "text-[--muted-fg]", bg: "bg-[--surface]",    border: "border-[--border]",     label: "Missing" },
  needs_verification: { icon: Upload,       color: "text-[--primary]",  bg: "bg-teal-950/20",    border: "border-teal-700/40",    label: "Needs Verification" },
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
        const cfg = DOC_CONFIG[doc.status];
        const Icon = cfg.icon;

        return (
          <motion.div
            key={doc.id}
            initial={{ x: -12, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: i * 0.05 }}
            className={cn(
              "flex items-start gap-3 rounded-xl border p-4 transition-colors",
              cfg.bg, cfg.border,
            )}
          >
            <Icon size={18} className={cn("mt-0.5 shrink-0", cfg.color)} />
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium text-[--foreground]">{doc.name}</p>
                <span className={cn(
                  "rounded-full px-2 py-0.5 text-[10px] font-medium",
                  doc.status === "accepted"   && "bg-emerald-500/20 text-[--success]",
                  doc.status === "rejected"   && "bg-red-500/20 text-[--danger]",
                  doc.status === "incomplete" && "bg-amber-500/20 text-amber-400",
                  doc.status === "missing"    && "bg-[--muted] text-[--muted-fg]",
                  doc.status === "needs_verification" && "bg-teal-500/20 text-[--primary]",
                )}>
                  {cfg.label}
                </span>
              </div>
              {doc.issues.length > 0 && (
                <ul className="mt-1.5 space-y-0.5">
                  {doc.issues.map((issue, j) => (
                    <li key={j} className="flex items-start gap-1 text-xs text-[--muted-fg]">
                      <span className="mt-0.5 shrink-0 text-[--danger]">•</span>
                      {issue}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            {(doc.status === "missing" || doc.status === "needs_verification") && onUpload && (
              <button
                onClick={() => onUpload(doc.name)}
                className="shrink-0 flex items-center gap-1.5 rounded-lg border border-[--primary]/40 px-3 py-1.5 text-xs text-[--primary] hover:bg-teal-950/40 transition-colors"
              >
                <Upload size={12} />
                Upload
              </button>
            )}
          </motion.div>
        );
      })}
    </div>
  );
}
