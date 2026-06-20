"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, ExternalLink } from "lucide-react";
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
            className="fixed inset-0 z-40 bg-black/40"
          />

          {/* Bottom sheet — slides up from the bottom on all screen sizes */}
          <motion.aside
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 280 }}
            className="fixed bottom-0 left-0 right-0 z-50 max-h-[85dvh] overflow-y-auto rounded-t-3xl bg-white shadow-2xl"
          >
            {/* Drag handle */}
            <div className="flex justify-center pb-2 pt-3">
              <div className="h-1.5 w-10 rounded-full bg-(--border)" />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between border-b border-(--border) px-5 pb-4">
              <h2 className="text-lg font-bold text-(--foreground)">About this step</h2>
              <button
                onClick={onClose}
                className="flex h-9 w-9 items-center justify-center rounded-full border border-(--border) text-(--muted-fg) hover:bg-(--surface) transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            {/* Body */}
            <div className="space-y-5 px-5 py-5 pb-10">
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-(--muted-fg)">
                  Step name
                </p>
                <p className="text-base font-semibold text-(--foreground)">{step.title}</p>
              </div>

              {step.description && (
                <div>
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-(--muted-fg)">
                    What to do
                  </p>
                  <p className="text-sm leading-relaxed text-(--foreground)">{step.description}</p>
                </div>
              )}

              {step.status === "locked" && (
                <div className="rounded-2xl border border-orange-200 bg-orange-50 p-4">
                  <p className="font-semibold text-orange-700">Why is this locked?</p>
                  <p className="mt-1 text-sm leading-relaxed text-orange-800">
                    {step.reason ||
                      "You need to finish the earlier steps first. Once those are done, this step will open for you automatically."}
                  </p>
                </div>
              )}

              {step.source_url && (
                <a
                  href={step.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 rounded-2xl border border-(--primary) bg-(--primary-light) p-4 text-sm font-semibold text-(--primary)"
                >
                  <ExternalLink size={16} />
                  View Official Government Page
                </a>
              )}

              <p className="text-xs leading-relaxed text-(--muted-fg)">
                This information comes from official Sri Lanka government sources. Always check
                with the relevant office for the latest requirements.
              </p>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

