"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, ExternalLink, BookOpen } from "lucide-react";
import type { Step } from "@/lib/types";

interface Props {
  step: Step | null;
  onClose: () => void;
}

export default function ExplainPanel({ step, onClose }: Props) {
  return (
    <AnimatePresence>
      {step && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
          />

          {/* Panel — slides in from right on desktop, bottom on mobile */}
          <motion.aside
            initial={{ x: "100%", opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: "100%", opacity: 0 }}
            transition={{ type: "spring", damping: 28, stiffness: 300 }}
            className="fixed right-0 top-0 z-50 flex h-full w-full flex-col border-l border-[--border] bg-[--surface] shadow-2xl sm:w-[420px]"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-[--border] p-5">
              <div className="flex items-center gap-2">
                <BookOpen size={18} className="text-[--primary]" />
                <span className="font-semibold text-[--foreground]">Why this step?</span>
              </div>
              <button
                onClick={onClose}
                className="rounded-lg p-1.5 text-[--muted-fg] hover:bg-[--muted] hover:text-[--foreground] transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              <div>
                <p className="text-xs text-[--muted-fg] uppercase tracking-wide mb-1">Step</p>
                <p className="font-medium text-[--foreground]">{step.title}</p>
              </div>

              {step.description && (
                <div>
                  <p className="text-xs text-[--muted-fg] uppercase tracking-wide mb-1">Description</p>
                  <p className="text-sm text-[--foreground] leading-relaxed">{step.description}</p>
                </div>
              )}

              {step.reason && (
                <div className="rounded-xl border border-amber-700/40 bg-amber-950/20 p-4">
                  <p className="text-xs text-amber-400 uppercase tracking-wide mb-1">Reason</p>
                  <p className="text-sm text-[--foreground] leading-relaxed">{step.reason}</p>
                </div>
              )}

              {step.status === "locked" && (
                <div className="rounded-xl border border-[--border] bg-[--surface] p-4 space-y-2">
                  <p className="text-xs text-[--muted-fg] uppercase tracking-wide">Why is this locked?</p>
                  <p className="text-sm text-[--foreground] leading-relaxed">
                    This step is blocked because a prerequisite has not been completed yet.
                    HelpLK AI prevents you from doing steps in the wrong order to avoid
                    rejected applications.
                  </p>
                </div>
              )}

              {step.source_url && (
                <div>
                  <p className="text-xs text-[--muted-fg] uppercase tracking-wide mb-2">Official Source</p>
                  <a
                    href={step.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 rounded-xl border border-[--primary]/40 bg-teal-950/20 p-3 text-sm text-[--primary] hover:bg-teal-950/40 transition-colors"
                  >
                    <ExternalLink size={14} />
                    View Official Government Page
                  </a>
                </div>
              )}

              <div className="rounded-xl border border-[--border] bg-[--muted]/30 p-4">
                <p className="text-xs text-[--muted-fg]">
                  Information in this panel is retrieved from verified official government sources via the
                  RAG Knowledge Agent. Always confirm with the relevant department for the latest updates.
                </p>
              </div>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
