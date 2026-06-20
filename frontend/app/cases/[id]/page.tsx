"use client";

import { useEffect, useRef, useState, use } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft, RefreshCw, Upload, Loader2, FileText,
  CheckSquare, Play, Cpu
} from "lucide-react";
import Navbar from "@/components/Navbar";
import WorkflowStep from "@/components/WorkflowStep";
import DocumentChecklist from "@/components/DocumentChecklist";
import ExplainPanel from "@/components/ExplainPanel";
import ProgressRing from "@/components/ProgressRing";
import { api } from "@/lib/api";
import type { Case, Step, Document } from "@/lib/types";
import { cn } from "@/lib/cn";

type Tab = "workflow" | "documents";

// Mock documents for demo (real data comes from backend documents API once M5 is implemented)
function mockDocs(steps: Step[]): Document[] {
  const needed: Document[] = [];
  const hasNIC     = steps.some((s) => s.title.toLowerCase().includes("nic") || s.title.toLowerCase().includes("police"));
  const hasBirth   = steps.some((s) => s.title.toLowerCase().includes("birth"));
  const hasPassport = steps.some((s) => s.title.toLowerCase().includes("passport"));

  if (hasNIC)     needed.push({ id: "d1", name: "National Identity Card (NIC)", type: "identity", status: "missing", issues: [] });
  if (hasNIC)     needed.push({ id: "d2", name: "Police Report", type: "report", status: "missing", issues: [] });
  if (hasBirth)   needed.push({ id: "d3", name: "Birth Certificate", type: "certificate", status: "missing", issues: [] });
  if (hasPassport) needed.push({
    id: "d4", name: "Passport Application Form", type: "form",
    status: "incomplete",
    issues: ["Signature missing on page 2", "Date field is empty"],
  });
  needed.push({ id: "d5", name: "Passport Photos (2×)", type: "photo", status: "needs_verification", issues: [] });
  return needed;
}

export default function CaseDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router  = useRouter();

  const [case_, setCase]  = useState<Case | null>(null);
  const [docs,  setDocs]  = useState<Document[]>([]);
  const [tab,   setTab]   = useState<Tab>("workflow");
  const [explain, setExplain] = useState<Step | null>(null);
  const [loading, setLoading] = useState(true);
  const [resuming, setResuming] = useState(false);
  const uploadRef = useRef<HTMLInputElement>(null);
  const [uploadFor, setUploadFor] = useState<string | null>(null);

  useEffect(() => {
    api.getCase(id)
      .then((c) => {
        setCase(c);
        setDocs(mockDocs(c.steps));
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [id]);

  async function handleResume() {
    setResuming(true);
    try {
      router.push(`/cases/${id}/processing`);
    } finally {
      setResuming(false);
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !uploadFor) return;
    // Update doc status optimistically
    setDocs((prev) => prev.map((d) => d.name === uploadFor ? { ...d, status: "needs_verification" } : d));
    await api.uploadDocument(id, file).catch(() => {});
    e.target.value = "";
    setUploadFor(null);
  }

  function openUpload(name: string) {
    setUploadFor(name);
    uploadRef.current?.click();
  }

  if (loading) {
    return (
      <div className="flex min-h-dvh flex-col bg-[--background]">
        <Navbar />
        <div className="flex flex-1 items-center justify-center">
          <Loader2 size={32} className="animate-spin text-[--primary]" />
        </div>
      </div>
    );
  }

  if (!case_) {
    return (
      <div className="flex min-h-dvh flex-col bg-[--background]">
        <Navbar />
        <div className="flex flex-1 flex-col items-center justify-center gap-4 px-4 text-center">
          <p className="text-[--muted-fg]">Case not found.</p>
          <button onClick={() => router.push("/dashboard")} className="text-sm text-[--primary] underline">
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const completedSteps = case_.steps.filter((s) => s.status === "completed").length;
  const nextStep       = case_.steps.find((s) => s.status === "active" || s.status === "pending");
  const lockedCount    = case_.steps.filter((s) => s.status === "locked").length;
  const acceptedDocs   = docs.filter((d) => d.status === "accepted").length;

  return (
    <div className="flex min-h-dvh flex-col bg-[--background]">
      <Navbar />
      <ExplainPanel step={explain} onClose={() => setExplain(null)} />

      {/* Hidden file input */}
      <input ref={uploadRef} type="file" className="hidden" onChange={handleUpload}
        accept="image/*,.pdf" />

      <main className="flex-1 px-4 py-8">
        <div className="mx-auto max-w-5xl">

          {/* Back */}
          <button
            onClick={() => router.push("/dashboard")}
            className="mb-6 flex items-center gap-1.5 text-sm text-[--muted-fg] hover:text-[--foreground] transition-colors"
          >
            <ArrowLeft size={15} /> Back to Dashboard
          </button>

          {/* ── Case header ─────────────────────────────────────────── */}
          <div className="mb-8 rounded-2xl border border-[--border] bg-[--surface] p-5 sm:p-6">
            <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2 mb-2">
                  <span className={cn(
                    "rounded-full px-2.5 py-0.5 text-xs font-medium",
                    case_.status === "completed" ? "bg-emerald-500/20 text-[--success]" : "bg-teal-500/15 text-[--primary]",
                  )}>
                    {case_.status === "completed" ? "Completed" : "In Progress"}
                  </span>
                  {lockedCount > 0 && (
                    <span className="rounded-full bg-amber-500/20 px-2.5 py-0.5 text-xs font-medium text-amber-400">
                      {lockedCount} locked
                    </span>
                  )}
                </div>
                <h1 className="text-xl font-bold text-[--foreground] sm:text-2xl leading-snug">
                  {case_.goal}
                </h1>
                {nextStep && (
                  <p className="mt-2 text-sm text-[--muted-fg]">
                    Next: <span className="text-[--foreground]">{nextStep.title}</span>
                  </p>
                )}
              </div>

              {/* Progress ring */}
              <div className="relative shrink-0 self-start">
                <ProgressRing progress={case_.progress} size={88} />
              </div>
            </div>

            {/* Stats row */}
            <div className="mt-5 grid grid-cols-3 gap-3 border-t border-[--border] pt-5">
              {[
                { label: "Steps done",    value: `${completedSteps} / ${case_.steps.length}` },
                { label: "Docs ready",    value: `${acceptedDocs} / ${docs.length}` },
                { label: "Locked steps",  value: lockedCount },
              ].map((s) => (
                <div key={s.label} className="text-center">
                  <p className="text-xl font-bold text-[--foreground]">{s.value}</p>
                  <p className="text-xs text-[--muted-fg]">{s.label}</p>
                </div>
              ))}
            </div>

            {/* Action buttons */}
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                onClick={handleResume}
                disabled={resuming}
                className="flex items-center gap-2 rounded-xl bg-[--primary] px-5 py-2.5 text-sm font-semibold text-white hover:bg-teal-500 transition-colors disabled:opacity-60"
              >
                {resuming ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
                {resuming ? "Resuming…" : "Resume Agents"}
              </button>
              <button
                onClick={() => openUpload("")}
                className="flex items-center gap-2 rounded-xl border border-[--border] px-5 py-2.5 text-sm text-[--foreground] hover:border-[--primary]/60 hover:bg-teal-950/20 transition-colors"
              >
                <Upload size={15} />
                Upload Document
              </button>
              <button
                onClick={() => { api.getCase(id).then(setCase); }}
                className="flex items-center gap-2 rounded-xl border border-[--border] px-4 py-2.5 text-sm text-[--muted-fg] hover:text-[--foreground] transition-colors"
                title="Refresh"
              >
                <RefreshCw size={15} />
              </button>
            </div>
          </div>

          {/* ── Tabs ────────────────────────────────────────────────── */}
          <div className="mb-6 flex gap-1 rounded-xl border border-[--border] bg-[--surface] p-1">
            {([
              { key: "workflow",  label: "Workflow",  icon: Cpu },
              { key: "documents", label: "Documents", icon: FileText },
            ] as const).map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setTab(key as Tab)}
                className={cn(
                  "flex flex-1 items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium transition-colors",
                  tab === key
                    ? "bg-[--primary] text-white shadow"
                    : "text-[--muted-fg] hover:text-[--foreground]",
                )}
              >
                <Icon size={15} />
                {label}
                {key === "documents" && docs.filter((d) => d.status === "missing").length > 0 && (
                  <span className="ml-1 rounded-full bg-[--danger] px-1.5 py-0.5 text-[10px] text-white">
                    {docs.filter((d) => d.status === "missing").length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* ── Tab content ─────────────────────────────────────────── */}
          <AnimatePresence mode="wait">
            {tab === "workflow" && (
              <motion.div
                key="workflow"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
              >
                {case_.steps.length === 0 ? (
                  <div className="rounded-2xl border border-[--border] bg-[--surface] p-10 text-center">
                    <Cpu size={36} className="mx-auto mb-3 text-[--muted-fg]" />
                    <p className="text-[--muted-fg]">Agents are still building your workflow.</p>
                    <button onClick={handleResume} className="mt-4 text-sm text-[--primary] underline">
                      Run agents now →
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
                      />
                    ))}
                  </div>
                )}
              </motion.div>
            )}

            {tab === "documents" && (
              <motion.div
                key="documents"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
              >
                {docs.length === 0 ? (
                  <div className="rounded-2xl border border-[--border] bg-[--surface] p-10 text-center">
                    <CheckSquare size={36} className="mx-auto mb-3 text-[--muted-fg]" />
                    <p className="text-[--muted-fg]">No documents identified yet.</p>
                    <button onClick={handleResume} className="mt-4 text-sm text-[--primary] underline">
                      Run agents to identify documents →
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
