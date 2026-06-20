"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus, Loader2, LayoutDashboard, Trash2, AlertCircle
} from "lucide-react";
import Navbar from "@/components/Navbar";
import CaseCard from "@/components/CaseCard";
import { api } from "@/lib/api";
import type { Case } from "@/lib/types";

export default function DashboardPage() {
  const [cases,   setCases]   = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);

  async function load() {
    try {
      // Ensure demo token exists
      if (!sessionStorage.getItem("helplk_token")) {
        const r = await fetch("/api/demo-token", { method: "POST" });
        const d = await r.json() as { token: string };
        sessionStorage.setItem("helplk_token", d.token);
      }
      const data = await api.listCases();
      setCases(data);
    } catch {
      setError("Could not reach the backend. Is it running?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleDelete(id: string) {
    setDeleting(id);
    await api.deleteCase(id).catch(() => {});
    setCases((prev) => prev.filter((c) => c.id !== id));
    setDeleting(null);
  }

  return (
    <div className="flex min-h-dvh flex-col bg-[--background]">
      <Navbar />

      <main className="flex-1 px-4 py-10">
        <div className="mx-auto max-w-4xl">

          {/* Header */}
          <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <LayoutDashboard size={20} className="text-[--primary]" />
                <h1 className="text-2xl font-bold text-[--foreground]">My Cases</h1>
              </div>
              <p className="text-sm text-[--muted-fg]">
                {loading ? "Loading…" : `${cases.length} active government procedure${cases.length !== 1 ? "s" : ""}`}
              </p>
            </div>
            <Link
              href="/goal"
              className="flex items-center gap-2 self-start rounded-xl bg-[--primary] px-5 py-2.5 text-sm font-semibold text-white hover:bg-teal-500 transition-colors sm:self-auto"
            >
              <Plus size={16} />
              New Procedure
            </Link>
          </div>

          {/* Loading */}
          {loading && (
            <div className="flex items-center justify-center py-24">
              <Loader2 size={32} className="animate-spin text-[--primary]" />
            </div>
          )}

          {/* Error */}
          {!loading && error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mb-6 flex items-start gap-3 rounded-xl border border-[--danger]/30 bg-red-950/20 p-4 text-sm"
            >
              <AlertCircle size={18} className="text-[--danger] mt-0.5 shrink-0" />
              <div>
                <p className="font-medium text-[--danger]">{error}</p>
                <p className="mt-1 text-xs text-[--muted-fg]">
                  Start the backend with <code className="font-mono">uvicorn app.main:app --reload</code>
                </p>
                <button onClick={load} className="mt-2 text-xs text-[--primary] underline">Retry</button>
              </div>
            </motion.div>
          )}

          {/* Empty state */}
          {!loading && !error && cases.length === 0 && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-[--border] bg-[--surface] py-24 text-center"
            >
              <LayoutDashboard size={40} className="mb-4 text-[--muted-fg]" />
              <h2 className="text-lg font-semibold text-[--foreground]">No cases yet</h2>
              <p className="mt-2 max-w-xs text-sm text-[--muted-fg]">
                Start by describing your government service need and HelpLK AI will plan everything for you.
              </p>
              <Link
                href="/goal"
                className="mt-6 flex items-center gap-2 rounded-xl bg-[--primary] px-6 py-2.5 text-sm font-semibold text-white hover:bg-teal-500 transition-colors"
              >
                <Plus size={15} />
                Start My First Procedure
              </Link>
            </motion.div>
          )}

          {/* Case list */}
          {!loading && !error && cases.length > 0 && (
            <div className="space-y-3">
              <AnimatePresence>
                {cases.map((c, i) => (
                  <motion.div
                    key={c.id}
                    layout
                    exit={{ opacity: 0, x: -16, height: 0 }}
                    transition={{ duration: 0.25 }}
                  >
                    {deleting === c.id ? (
                      <div className="flex items-center justify-center rounded-2xl border border-[--border] bg-[--surface] py-6">
                        <Loader2 size={18} className="animate-spin text-[--muted-fg]" />
                      </div>
                    ) : (
                      <CaseCard case_={c} index={i} onDelete={handleDelete} />
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}

          {/* Quick tip */}
          {!loading && cases.length > 0 && (
            <p className="mt-8 text-center text-xs text-[--muted-fg]">
              Hover a case and click <Trash2 size={10} className="inline" /> to delete it ·
              Click <strong>Continue</strong> to resume where you left off
            </p>
          )}
        </div>
      </main>
    </div>
  );
}
