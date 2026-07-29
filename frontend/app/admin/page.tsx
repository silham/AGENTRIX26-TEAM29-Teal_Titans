"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { AlertCircle, Database, Loader2, Search } from "lucide-react";
import Navbar from "@/components/Navbar";
import KnowledgeTable from "@/components/KnowledgeTable";
import KnowledgeUploader from "@/components/KnowledgeUploader";
import { api, isAdmin, isAuthenticated } from "@/lib/api";
import type { KnowledgeDoc, KnowledgeSearchHit, KnowledgeStats } from "@/lib/types";

const POLL_MS = 2000;

export default function AdminPage() {
  const router = useRouter();

  const [allowed, setAllowed] = useState(false);
  const [docs, setDocs]       = useState<KnowledgeDoc[]>([]);
  const [stats, setStats]     = useState<KnowledgeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState("");
  const [busyId, setBusyId]   = useState<string | null>(null);

  const [query, setQuery]     = useState("");
  const [hits, setHits]       = useState<KnowledgeSearchHit[] | null>(null);
  const [searching, setSearching] = useState(false);

  // Cosmetic gate only — the backend's require_admin is the real boundary and
  // will 403 every call below regardless of what sessionStorage says.
  useEffect(() => {
    if (!isAuthenticated()) { router.replace("/auth?next=/admin"); return; }
    if (!isAdmin())         { router.replace("/dashboard"); return; }
    setAllowed(true);
  }, [router]);

  const load = useCallback(async () => {
    try {
      const [listing, s] = await Promise.all([api.admin.listKnowledge(), api.admin.stats()]);
      setDocs(listing.documents);
      setStats(s);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load the knowledge base.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { if (allowed) void load(); }, [allowed, load]);

  // Ingestion is async, so poll while anything is still in flight — and stop
  // as soon as everything settles.
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    const inFlight = docs.some((d) => d.status === "pending" || d.status === "processing");
    if (allowed && inFlight && !timer.current) {
      timer.current = setInterval(() => { void load(); }, POLL_MS);
    }
    if ((!inFlight || !allowed) && timer.current) {
      clearInterval(timer.current);
      timer.current = null;
    }
    return () => {
      if (timer.current) { clearInterval(timer.current); timer.current = null; }
    };
  }, [docs, allowed, load]);

  async function handleReindex(id: string) {
    setBusyId(id);
    try { await api.admin.reindex(id); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "Reindex failed."); }
    finally { setBusyId(null); }
  }

  async function handleDelete(id: string) {
    setBusyId(id);
    try {
      await api.admin.remove(id);
      setDocs((prev) => prev.filter((d) => d.id !== id));
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleSearch() {
    if (query.trim().length < 2) return;
    setSearching(true);
    try { setHits((await api.admin.search(query.trim())).hits); }
    catch (e) { setError(e instanceof Error ? e.message : "Search failed."); }
    finally { setSearching(false); }
  }

  if (!allowed) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-(--background)">
        <Loader2 size={32} className="animate-spin text-(--primary)" />
      </div>
    );
  }

  const retrieval = stats?.retrieval;

  return (
    <div className="flex min-h-dvh flex-col bg-(--background)">
      <Navbar />

      <main className="flex-1 px-4 py-6">
        <div className="mx-auto max-w-3xl">

          <div className="mb-2 flex items-center gap-2">
            <Database size={22} className="text-(--primary)" />
            <h1 className="text-xl font-bold text-(--foreground)">Knowledge Base</h1>
          </div>
          <p className="mb-5 text-sm text-(--muted-fg)">
            Government documents uploaded here are indexed and used to answer citizen
            questions, with each answer citing the document it came from.
          </p>

          {/* Retrieval health — this is where failures the agent graph swallows
              silently become visible. */}
          {stats && (
            <div className="mb-5 grid grid-cols-3 gap-3">
              {[
                { label: "Documents", value: stats.documents },
                { label: "Indexed chunks", value: stats.chunks },
                { label: "Retrieval", value: retrieval?.ok ? "Online" : "Offline" },
              ].map((tile) => (
                <div key={tile.label} className="rounded-2xl border border-(--border) bg-white p-3 text-center">
                  <p className="text-lg font-bold text-(--foreground)">{tile.value}</p>
                  <p className="text-xs text-(--muted-fg)">{tile.label}</p>
                </div>
              ))}
            </div>
          )}

          {retrieval && !retrieval.ok && retrieval.error && (
            <div className="mb-5 flex items-start gap-3 rounded-2xl border border-red-200 bg-(--danger-light) p-4">
              <AlertCircle size={18} className="mt-0.5 shrink-0 text-(--danger)" />
              <div>
                <p className="text-sm font-semibold text-(--danger)">Retrieval is unavailable</p>
                <p className="mt-1 text-xs text-(--muted-fg)">{retrieval.error}</p>
              </div>
            </div>
          )}

          {retrieval?.ok && retrieval.unstamped_chunks > 0 && (
            <div className="mb-5 rounded-2xl border border-orange-200 bg-orange-50 p-4">
              <p className="text-sm font-semibold text-orange-800">
                {retrieval.unstamped_chunks} chunk(s) have unknown provenance
              </p>
              <p className="mt-1 text-xs text-orange-700">
                They were indexed before the embedding model was recorded, so they are
                excluded from search. Reindex them to bring them back.
              </p>
            </div>
          )}

          <div className="mb-5">
            <KnowledgeUploader onUploaded={() => void load()} />
          </div>

          {/* Retrieval smoke test — the fastest way to confirm a new upload is live. */}
          <div className="mb-5 rounded-2xl border border-(--border) bg-white p-4">
            <p className="mb-2 text-sm font-semibold text-(--foreground)">Test retrieval</p>
            <div className="flex gap-2">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") void handleSearch(); }}
                placeholder="Ask what a citizen might ask…"
                className="flex-1 rounded-xl border border-(--border) px-3 py-2.5 text-sm outline-none focus:border-(--primary)"
              />
              <button
                onClick={() => void handleSearch()}
                disabled={searching || query.trim().length < 2}
                className="flex items-center gap-1.5 rounded-xl bg-(--primary) px-4 py-2.5 text-sm font-bold text-white hover:bg-(--primary-dark) disabled:opacity-40 active:scale-95 transition-all"
              >
                {searching ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
                Search
              </button>
            </div>

            {hits !== null && (
              <div className="mt-3 space-y-2">
                {hits.length === 0 && (
                  <p className="text-sm text-(--muted-fg)">
                    Nothing scored above the relevance threshold. Try different wording, or
                    upload a document covering this topic.
                  </p>
                )}
                {hits.map((hit, i) => (
                  <div key={i} className="rounded-xl bg-(--surface) p-3">
                    <div className="flex items-baseline justify-between gap-2">
                      <p className="truncate text-sm font-semibold text-(--foreground)">
                        {hit.title || "Untitled"}
                      </p>
                      <span className="shrink-0 text-xs font-mono text-(--muted-fg)">
                        {hit.score.toFixed(3)}
                      </span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs text-(--muted-fg)">{hit.snippet}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mb-5 flex items-start gap-3 rounded-2xl border border-red-200 bg-(--danger-light) p-4"
            >
              <AlertCircle size={18} className="mt-0.5 shrink-0 text-(--danger)" />
              <p className="text-sm text-(--danger)">{error}</p>
            </motion.div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 size={32} className="animate-spin text-(--primary)" />
            </div>
          ) : (
            <KnowledgeTable
              documents={docs}
              busyId={busyId}
              onReindex={(id) => void handleReindex(id)}
              onDelete={(id) => void handleDelete(id)}
            />
          )}

        </div>
      </main>
    </div>
  );
}
