"use client";

import { useEffect, useRef, useState, use } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft, Upload, Loader2, FileText, CheckSquare, CheckCircle2, Play, RefreshCw,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import WorkflowStep from "@/components/WorkflowStep";
import DocumentChecklist from "@/components/DocumentChecklist";
import ExplainPanel from "@/components/ExplainPanel";
import { api } from "@/lib/api";
import type { Case, Step, Document } from "@/lib/types";
import { cn } from "@/lib/cn";

type Tab = "steps" | "documents";

export default function CaseDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id }   = use(params);
  const router   = useRouter();

  const [case_,    setCase]    = useState<Case | null>(null);
  const [tab,      setTab]     = useState<Tab>("steps");
  const [explain,  setExplain] = useState<Step | null>(null);
  const [loading,  setLoading] = useState(true);
  const [uploadFor, setUploadFor] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [togglingStep, setTogglingStep] = useState<string | null>(null);
  const uploadRef  = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.getCase(id)
      .then((c) => { setCase(c); setLoading(false); })
      .catch(() => setLoading(false));
  }, [id]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await api.uploadDocument(id, file, uploadFor || file.name);
      // Re-fetch: the backend verified the upload (Gemini Vision / OCR) and
      // updated the document row — show the real verdict.
      const updated = await api.getCase(id);
      setCase(updated);
    } catch { /* keep current view; user can retry */ }
    e.target.value = "";
    setUploadFor(null);
    setUploading(false);
  }

  function openUpload(name: string) {
    setUploadFor(name);
    uploadRef.current?.click();
  }

  async function toggleStep(step: Step) {
    setTogglingStep(step.id);
    try {
      const updated = await api.updateStep(
        id,
        step.id,
        step.status === "completed" ? "pending" : "completed",
      );
      setCase(updated); // backend returns the recomputed case (locks, progress, active step)
    } catch {
      // leave the UI unchanged; the refresh button re-syncs on demand
    } finally {
      setTogglingStep(null);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-dvh flex-col bg-(--background)">
        <Navbar />
        <div className="flex flex-1 items-center justify-center">
          <Loader2 size={36} className="animate-spin text-(--primary)" />
        </div>
      </div>
    );
  }

  if (!case_) {
    return (
      <div className="flex min-h-dvh flex-col bg-(--background)">
        <Navbar />
        <div className="flex flex-1 flex-col items-center justify-center gap-4 px-4 text-center">
          <p className="text-(--muted-fg)">This plan was not found.</p>
          <button
            onClick={() => router.push("/dashboard")}
            className="text-sm font-semibold text-(--primary) underline"
          >
            Back to My Plans
          </button>
        </div>
      </div>
    );
  }

  const completedSteps  = case_.steps.filter((s) => s.status === "completed").length;
  const nextStep        = case_.steps.find((s) => s.status === "active" || s.status === "pending");
  const allDone         = case_.steps.length > 0 &&
    case_.steps.every((s) => s.status === "completed" || s.status === "skipped");
  const docs            = case_.documents ?? [];
  const missingDocCount = docs.filter((d) => d.status === "missing").length;

  const TABS = [
    { key: "steps" as Tab,     label: "Your Steps", Icon: CheckSquare, badge: 0 },
    { key: "documents" as Tab, label: "Documents",  Icon: FileText,    badge: missingDocCount },
  ];

  return (
    <div className="flex min-h-dvh flex-col bg-(--surface)">
      <Navbar />
      <ExplainPanel step={explain} onClose={() => setExplain(null)} />
      <input ref={uploadRef} type="file" className="hidden" onChange={handleUpload} accept="image/*,.pdf" />

      <main className="flex-1 px-4 py-4">
        <div className="mx-auto max-w-lg">

          {/* Back */}
          <button
            onClick={() => router.push("/dashboard")}
            className="mb-4 flex items-center gap-1.5 text-sm text-(--muted-fg) hover:text-(--foreground) transition-colors"
          >
            <ArrowLeft size={16} /> Back to My Plans
          </button>

          {/* Case header */}
          <div className="mb-4 rounded-2xl border border-(--border) bg-white p-5 shadow-sm">
            <span className={cn(
              "mb-2 inline-block rounded-full px-3 py-0.5 text-xs font-semibold",
              case_.status === "completed"
                ? "bg-(--success-light) text-(--success)"
                : "bg-(--primary-light) text-(--primary)",
            )}>
              {case_.status === "completed" ? "Completed" : "In Progress"}
            </span>

            <h1 className="text-lg font-bold leading-snug text-(--foreground)">
              {case_.goal}
            </h1>

            {nextStep && (
              <p className="mt-2 text-sm text-(--muted-fg)">
                Next step:{" "}
                <span className="font-semibold text-(--foreground)">{nextStep.title}</span>
              </p>
            )}

            {/* Progress bar */}
            <div className="mt-4">
              <div className="mb-1.5 flex items-center justify-between text-sm">
                <span className="text-(--muted-fg)">
                  {completedSteps} of {case_.steps.length} steps done
                </span>
                <span className="font-bold text-(--primary)">{case_.progress}%</span>
              </div>
              <div className="h-3 w-full overflow-hidden rounded-full bg-(--surface)">
                <motion.div
                  className="h-full rounded-full bg-(--primary)"
                  initial={{ width: 0 }}
                  animate={{ width: `${case_.progress}%` }}
                  transition={{ duration: 0.8, ease: "easeOut" }}
                />
              </div>
            </div>

            {/* Actions */}
            <div className="mt-4 flex gap-2">
              {case_.steps.length === 0 ? (
                <button
                  onClick={() => router.push(`/cases/${id}/processing`)}
                  className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-(--primary) py-3 text-sm font-bold text-white hover:bg-(--primary-dark) active:scale-95 transition-all"
                >
                  <Play size={15} /> Generate Plan
                </button>
              ) : nextStep ? (
                <button
                  onClick={() => toggleStep(nextStep)}
                  disabled={togglingStep !== null}
                  className="flex flex-1 items-center justify-center gap-2 whitespace-nowrap rounded-xl bg-(--primary) px-3 py-3 text-sm font-bold text-white hover:bg-(--primary-dark) active:scale-95 transition-all disabled:opacity-60"
                >
                  {togglingStep === nextStep.id
                    ? <Loader2 size={15} className="shrink-0 animate-spin" />
                    : <CheckCircle2 size={15} className="shrink-0" />}
                  Complete Step
                </button>
              ) : allDone ? (
                <div className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-(--success-light) py-3 text-sm font-bold text-(--success)">
                  <CheckCircle2 size={15} /> All Steps Done
                </div>
              ) : (
                <div className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-orange-50 py-3 text-sm font-bold text-orange-700">
                  ⛔ Not Eligible — see steps below
                </div>
              )}
              <button
                onClick={() => openUpload("")}
                className="flex shrink-0 items-center gap-2 whitespace-nowrap rounded-xl border border-(--border) bg-white px-4 py-3 text-sm font-medium text-(--foreground) hover:border-(--primary) transition-colors"
              >
                <Upload size={15} /> Upload
              </button>
              <button
                onClick={() => { api.getCase(id).then(setCase).catch(() => {}); }}
                className="flex items-center justify-center rounded-xl border border-(--border) bg-white px-3 py-3 text-(--muted-fg) hover:text-(--foreground) transition-colors"
                title="Refresh"
              >
                <RefreshCw size={15} />
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="mb-4 grid grid-cols-2 gap-1 rounded-2xl border border-(--border) bg-white p-1 shadow-sm">
            {TABS.map(({ key, label, Icon, badge }) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={cn(
                  "flex items-center justify-center gap-2 rounded-xl py-3 text-sm font-semibold transition-colors",
                  tab === key
                    ? "bg-(--primary) text-white shadow"
                    : "text-(--muted-fg) hover:text-(--foreground)",
                )}
              >
                <Icon size={16} />
                {label}
                {badge > 0 && (
                  <span className={cn(
                    "rounded-full px-1.5 py-0.5 text-[10px] font-bold",
                    tab === key ? "bg-white/30 text-white" : "bg-(--danger) text-white",
                  )}>
                    {badge}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <AnimatePresence mode="wait">
            {tab === "steps" && (
              <motion.div
                key="steps"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                {case_.steps.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-(--border) bg-white p-10 text-center">
                    <CheckSquare size={36} className="mx-auto mb-3 text-(--muted-fg)" />
                    <p className="text-sm text-(--muted-fg)">
                      No steps yet. Resume to generate your plan.
                    </p>
                    <button
                      onClick={() => router.push(`/cases/${id}/processing`)}
                      className="mt-4 text-sm font-semibold text-(--primary) underline"
                    >
                      Generate plan →
                    </button>
                  </div>
                ) : (
                  <div>
                    {case_.steps.map((step, i) => (
                      <WorkflowStep
                        key={step.id}
                        step={step}
                        index={i}
                        isLast={i === case_.steps.length - 1}
                        onExplain={setExplain}
                        onToggle={toggleStep}
                        busy={togglingStep === step.id}
                      />
                    ))}
                  </div>
                )}
              </motion.div>
            )}

            {tab === "documents" && (
              <motion.div
                key="documents"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                {docs.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-(--border) bg-white p-10 text-center">
                    <FileText size={36} className="mx-auto mb-3 text-(--muted-fg)" />
                    <p className="text-sm text-(--muted-fg)">No documents identified yet.</p>
                    <button
                      onClick={() => router.push(`/cases/${id}/processing`)}
                      className="mt-4 text-sm font-semibold text-(--primary) underline"
                    >
                      Generate plan to see documents →
                    </button>
                  </div>
                ) : (
                  <DocumentChecklist documents={docs} onUpload={openUpload} />
                )}
              </motion.div>
            )}
          </AnimatePresence>

        </div>
      </main>
    </div>
  );
}
