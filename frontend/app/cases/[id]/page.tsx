"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft, CornerUpLeft, Loader2, ListChecks, CheckSquare, CheckCircle2, Play, RefreshCw,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import WorkflowStep from "@/components/WorkflowStep";
import RequirementChecklist from "@/components/RequirementChecklist";
import ExplainPanel from "@/components/ExplainPanel";
import CitationList from "@/components/CitationList";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import type { Case, Requirement, Step } from "@/lib/types";
import { SATISFIED } from "@/lib/types";
import { cn } from "@/lib/cn";

type Tab = "steps" | "requirements";

export default function CaseDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id }   = use(params);
  const router   = useRouter();
  const t        = useT();

  const [case_,    setCase]    = useState<Case | null>(null);
  const [tab,      setTab]     = useState<Tab>("steps");
  const [explain,  setExplain] = useState<Step | null>(null);
  const [loading,  setLoading] = useState(true);
  const [busyReq,  setBusyReq] = useState<string | null>(null);
  const [togglingStep, setTogglingStep] = useState<string | null>(null);

  useEffect(() => {
    api.getCase(id)
      .then((c) => { setCase(c); setLoading(false); })
      .catch(() => setLoading(false));
  }, [id]);

  // "I have it" / undo. The response is the recomputed case, so steps,
  // progress and the requirement all update in one round trip.
  async function markRequirement(req: Requirement, next: "confirmed" | "missing") {
    setBusyReq(req.id);
    try {
      setCase(await api.setRequirement(id, req.id, next));
    } catch {
      // leave the UI unchanged; the refresh button re-syncs on demand
    } finally {
      setBusyReq(null);
    }
  }

  // "How to get it?" — a brand-new plan has no steps yet and needs the agent
  // graph to run; an existing one goes straight to its checklist.
  async function startSubGoal(req: Requirement) {
    setBusyReq(req.id);
    try {
      const sub = await api.createSubGoal(id, req.id);
      router.push(sub.steps.length === 0 ? `/cases/${sub.id}/processing` : `/cases/${sub.id}`);
    } catch {
      setBusyReq(null);
    }
    // deliberately no finally: stay busy through the navigation
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
          <p className="text-(--muted-fg)">{t("case.notFound")}</p>
          <button
            onClick={() => router.push("/dashboard")}
            className="text-sm font-semibold text-(--primary) underline"
          >
            {t("case.back")}
          </button>
        </div>
      </div>
    );
  }

  const completedSteps  = case_.steps.filter((s) => s.status === "completed").length;
  const nextStep        = case_.steps.find((s) => s.status === "active" || s.status === "pending");
  const allDone         = case_.steps.length > 0 &&
    case_.steps.every((s) => s.status === "completed" || s.status === "skipped");
  const requirements    = case_.documents ?? [];
  const citations       = case_.citations ?? [];
  const subGoals        = case_.sub_goals ?? [];
  // Everything still outstanding — which correctly includes legacy
  // rejected/incomplete rows, not just "missing".
  const openReqCount    = requirements.filter((r) => !SATISFIED.has(r.status)).length;

  const TABS = [
    { key: "steps" as Tab,        label: t("case.tabSteps"),        Icon: CheckSquare, badge: 0 },
    { key: "requirements" as Tab, label: t("case.tabRequirements"), Icon: ListChecks,  badge: openReqCount },
  ];

  return (
    <div className="flex min-h-dvh flex-col bg-(--surface)">
      <Navbar />
      <ExplainPanel step={explain} onClose={() => setExplain(null)} />

      <main className="flex-1 px-4 py-4">
        <div className="mx-auto max-w-lg">

          {/* Back */}
          <button
            onClick={() => router.push("/dashboard")}
            className="mb-4 flex items-center gap-1.5 text-sm text-(--muted-fg) hover:text-(--foreground) transition-colors"
          >
            <ArrowLeft size={16} /> {t("case.back")}
          </button>

          {/* Case header */}
          <div className="mb-4 rounded-2xl border border-(--border) bg-white p-5 shadow-sm">
            <span className={cn(
              "mb-2 inline-block rounded-full px-3 py-0.5 text-xs font-semibold",
              case_.status === "completed"
                ? "bg-(--success-light) text-(--success)"
                : "bg-(--primary-light) text-(--primary)",
            )}>
              {case_.status === "completed" ? t("case.completed") : t("case.inProgress")}
            </span>

            {/* This plan exists to obtain one requirement of another plan. */}
            {case_.parent && (
              <Link
                href={`/cases/${case_.parent.id}`}
                className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-(--muted-fg) hover:text-(--primary) transition-colors"
              >
                <CornerUpLeft size={12} className="shrink-0" />
                <span className="line-clamp-1">
                  {t("case.partOf", { goal: case_.parent.goal })}
                </span>
              </Link>
            )}

            <h1 className="text-lg font-bold leading-snug text-(--foreground)">
              {case_.goal}
            </h1>

            {nextStep && (
              <p className="mt-2 text-sm text-(--muted-fg)">
                {t("case.nextStep")}{" "}
                <span className="font-semibold text-(--foreground)">{nextStep.title}</span>
              </p>
            )}

            {/* Progress bar */}
            <div className="mt-4">
              <div className="mb-1.5 flex items-center justify-between text-sm">
                <span className="text-(--muted-fg)">
                  {t("case.stepsDone", {
                    count: case_.steps.length,
                    done: completedSteps,
                    total: case_.steps.length,
                  })}
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
                  <Play size={15} /> {t("case.generatePlan")}
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
                  {t("case.completeStep")}
                </button>
              ) : allDone ? (
                <div className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-(--success-light) py-3 text-sm font-bold text-(--success)">
                  <CheckCircle2 size={15} /> {t("case.allDone")}
                </div>
              ) : (
                <div className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-orange-50 py-3 text-sm font-bold text-orange-700">
                  {t("case.notEligible")}
                </div>
              )}
              <button
                onClick={() => { api.getCase(id).then(setCase).catch(() => {}); }}
                className="flex items-center justify-center rounded-xl border border-(--border) bg-white px-3 py-3 text-(--muted-fg) hover:text-(--foreground) transition-colors"
                title={t("case.refresh")}
                aria-label={t("case.refresh")}
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
                      {t("case.emptySteps")}
                    </p>
                    <button
                      onClick={() => router.push(`/cases/${id}/processing`)}
                      className="mt-4 text-sm font-semibold text-(--primary) underline"
                    >
                      {t("case.emptyStepsCta")}
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

                {/* Where the plan's information came from. Official procedure and
                    supporting uploaded documents are shown separately on purpose. */}
                {citations.length > 0 && (
                  <div className="mt-6 border-t border-(--border) pt-5">
                    <CitationList citations={citations} />
                  </div>
                )}
              </motion.div>
            )}

            {tab === "requirements" && (
              <motion.div
                key="requirements"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                {requirements.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-(--border) bg-white p-10 text-center">
                    <ListChecks size={36} className="mx-auto mb-3 text-(--muted-fg)" />
                    <p className="text-sm text-(--muted-fg)">{t("case.emptyRequirements")}</p>
                    <button
                      onClick={() => router.push(`/cases/${id}/processing`)}
                      className="mt-4 text-sm font-semibold text-(--primary) underline"
                    >
                      {t("case.emptyRequirementsCta")}
                    </button>
                  </div>
                ) : (
                  <RequirementChecklist
                    requirements={requirements}
                    subGoals={subGoals}
                    onHaveIt={markRequirement}
                    onHowToGet={startSubGoal}
                    busyId={busyReq}
                  />
                )}

                {/* Plans started from these requirements. They live here rather
                    than in a third tab because they are requirement-derived. */}
                {subGoals.length > 0 && (
                  <div className="mt-6 border-t border-(--border) pt-5">
                    <p className="mb-3 text-sm font-bold text-(--foreground)">
                      {t("case.subGoalsTitle")}
                    </p>
                    <div className="space-y-2">
                      {subGoals.map((g) => (
                        <Link
                          key={g.id}
                          href={`/cases/${g.id}`}
                          className="block rounded-2xl border border-(--border) bg-white p-4 hover:border-(--primary) transition-colors"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <p className="line-clamp-1 text-sm font-semibold text-(--foreground)">
                              {g.goal}
                            </p>
                            <span className="shrink-0 text-xs font-bold text-(--primary)">
                              {g.progress}%
                            </span>
                          </div>
                          <div className="mt-2 h-2 overflow-hidden rounded-full bg-(--surface)">
                            <div
                              className="h-full rounded-full bg-(--primary) transition-all"
                              style={{ width: `${g.progress}%` }}
                            />
                          </div>
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

        </div>
      </main>
    </div>
  );
}
