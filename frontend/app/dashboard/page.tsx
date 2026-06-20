"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Loader2, ClipboardList, AlertCircle } from "lucide-react";
import Navbar from "@/components/Navbar";
import CaseCard from "@/components/CaseCard";
import { api } from "@/lib/api";
import type { Case } from "@/lib/types";

export default function DashboardPage() {
  const [cases,    setCases]    = useState<Case[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);

  async function load() {
    try {
      if (!sessionStorage.getItem("helplk_token")) {
        const r = await fetch("/api/demo-token", { method: "POST" });
        const d = await r.json() as { token: string };
        sessionStorage.setItem("helplk_token", d.token);
      }
      const data = await api.listCases();
      setCases(data);
    } catch {
      setError("Could not load your plans. Is the server running?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  async function handleDelete(id: string) {
    setDeleting(id);
    await api.deleteCase(id).catch(() => {});
    setCases((prev) => prev.filter((c) => c.id !== id));
    setDeleting(null);
  }

  return (
    <div className="flex min-h-dvh flex-col bg-(--background)">
      <Navbar />

      <main className="flex-1 px-4 py-6">
        <div className="mx-auto max-w-lg">

          {/* Header */}
          <div className="mb-5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ClipboardList size={22} className="text-(--primary)" />
              <h1 className="text-xl font-bold text-(--foreground)">My Plans</h1>
            </div>
            <Link
              href="/goal"
              className="flex items-center gap-1.5 rounded-xl bg-(--primary) px-4 py-2.5 text-sm font-bold text-white hover:bg-(--primary-dark) active:scale-95 transition-all"
            >
              <Plus size={16} /> New Plan
            </Link>
          </div>

          {/* Loading */}
          {loading && (
            <div className="flex items-center justify-center py-24">
              <Loader2 size={36} className="animate-spin text-(--primary)" />
            </div>
          )}

          {/* Error */}
          {!loading && error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mb-5 flex items-start gap-3 rounded-2xl border border-red-200 bg-(--danger-light) p-4"
            >
              <AlertCircle size={20} className="mt-0.5 shrink-0 text-(--danger)" />
              <div>
                <p className="text-sm font-semibold text-(--danger)">{error}</p>
                <p className="mt-1 text-xs text-(--muted-fg)">
                  Start the backend:{" "}
                  <code className="rounded bg-white px-1 font-mono text-xs">
                    uvicorn app.main:app --reload
                  </code>
                </p>
                <button
                  onClick={() => { void load(); }}
                  className="mt-2 text-xs font-semibold text-(--primary) underline"
                >
                  Try again
                </button>
              </div>
            </motion.div>
          )}

          {/* Empty state */}
          {!loading && !error && cases.length === 0 && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-(--border) bg-white px-6 py-20 text-center"
            >
              <ClipboardList size={44} className="mb-4 text-(--muted-fg)" />
              <h2 className="text-lg font-bold text-(--foreground)">No plans yet</h2>
              <p className="mt-2 max-w-xs text-sm leading-relaxed text-(--muted-fg)">
                Start by telling us what government service you need help with.
                We will build a step-by-step guide just for you.
              </p>
              <Link
                href="/goal"
                className="mt-6 flex items-center gap-2 rounded-2xl bg-(--primary) px-8 py-4 text-base font-bold text-white hover:bg-(--primary-dark) active:scale-95 transition-all"
              >
                <Plus size={18} /> Start My First Plan
              </Link>
            </motion.div>
          )}

          {/* Case list */}
          {!loading && !error && cases.length > 0 && (
            <div className="space-y-3">
              <p className="text-sm text-(--muted-fg)">
                {cases.length} active plan{cases.length !== 1 ? "s" : ""}
              </p>
              <AnimatePresence>
                {cases.map((c, i) => (
                  <motion.div
                    key={c.id}
                    layout
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.25 }}
                  >
                    {deleting === c.id ? (
                      <div className="flex items-center justify-center rounded-2xl border border-(--border) bg-white py-8">
                        <Loader2 size={20} className="animate-spin text-(--muted-fg)" />
                      </div>
                    ) : (
                      <CaseCard case_={c} index={i} onDelete={handleDelete} />
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}

