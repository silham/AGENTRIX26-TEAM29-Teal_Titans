"use client";

import { motion } from "framer-motion";
import {
  CheckCircle2, XCircle, Loader2, Clock, RefreshCw, Trash2, ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/cn";
import type { KnowledgeDoc, KnowledgeStatus } from "@/lib/types";

const STATUS_CFG: Record<KnowledgeStatus, {
  Icon: typeof CheckCircle2; iconClass: string; badge: string; badgeClass: string;
}> = {
  ready: {
    Icon: CheckCircle2,
    iconClass: "text-(--success)",
    badge: "Indexed",
    badgeClass: "bg-green-100 text-(--success)",
  },
  processing: {
    Icon: Loader2,
    iconClass: "text-(--primary) animate-spin",
    badge: "Indexing…",
    badgeClass: "bg-blue-100 text-(--primary)",
  },
  pending: {
    Icon: Clock,
    iconClass: "text-(--muted-fg)",
    badge: "Queued",
    badgeClass: "bg-(--surface) text-(--muted-fg)",
  },
  failed: {
    Icon: XCircle,
    iconClass: "text-(--danger)",
    badge: "Failed",
    badgeClass: "bg-red-100 text-(--danger)",
  },
};

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

interface Props {
  documents: KnowledgeDoc[];
  busyId: string | null;
  onReindex: (id: string) => void;
  onDelete: (id: string) => void;
}

export default function KnowledgeTable({ documents, busyId, onReindex, onDelete }: Props) {
  if (!documents.length) {
    return (
      <div className="rounded-2xl border border-dashed border-(--border) bg-white px-6 py-16 text-center">
        <p className="text-base font-semibold text-(--foreground)">No documents yet</p>
        <p className="mt-2 text-sm text-(--muted-fg)">
          Upload a government circular, form or instruction sheet above. Once indexed,
          citizen answers will be grounded in it and cite it as a source.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {documents.map((doc, i) => {
        const cfg  = STATUS_CFG[doc.status];
        const Icon = cfg.Icon;
        const busy = busyId === doc.id;
        // Seeded corpus files have no stored upload to re-read.
        const seeded = doc.uploaded_by === "corpus-cli";

        return (
          <motion.div
            key={doc.id}
            initial={{ y: 8, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: Math.min(i * 0.04, 0.3) }}
            className="rounded-2xl border border-(--border) bg-white p-4"
          >
            <div className="flex items-start gap-3">
              <Icon size={20} className={cn("mt-0.5 shrink-0", cfg.iconClass)} />

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <p className="truncate text-base font-semibold text-(--foreground)">
                    {doc.title || doc.filename}
                  </p>
                  <span className={cn("shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold", cfg.badgeClass)}>
                    {cfg.badge}
                  </span>
                </div>

                <p className="mt-0.5 truncate text-xs text-(--muted-fg)">
                  {doc.filename} · {humanSize(doc.size_bytes)} · {doc.uploaded_by}
                </p>

                {doc.source_url && (
                  <a
                    href={doc.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 inline-flex max-w-full items-center gap-1 truncate text-xs font-medium text-(--primary) hover:underline"
                  >
                    <ExternalLink size={11} className="shrink-0" />
                    <span className="truncate">{doc.source_url}</span>
                  </a>
                )}

                {doc.status === "ready" && (
                  <p className="mt-2 text-xs text-(--muted-fg)">
                    {doc.chunk_count} chunk{doc.chunk_count !== 1 ? "s" : ""}
                    {doc.page_count ? ` · ${doc.page_count} page${doc.page_count !== 1 ? "s" : ""}` : ""}
                    {doc.char_count ? ` · ${doc.char_count.toLocaleString()} chars` : ""}
                    {doc.extraction_method ? ` · read via ${doc.extraction_method}` : ""}
                    {doc.embedding_model ? ` · ${doc.embedding_model}` : ""}
                  </p>
                )}

                {/* The backend writes admin-facing, actionable messages here. */}
                {doc.error && (
                  <p className="mt-2 rounded-xl bg-(--danger-light) p-2.5 text-xs leading-relaxed text-(--danger)">
                    {doc.error}
                  </p>
                )}
              </div>
            </div>

            <div className="mt-3 flex gap-2">
              <button
                onClick={() => onReindex(doc.id)}
                disabled={busy || seeded || doc.status === "processing"}
                title={seeded ? "Seeded by the corpus CLI — re-run `python -m app.rag.ingest`" : undefined}
                className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-(--border) py-2.5 text-sm font-semibold text-(--foreground) hover:bg-(--surface) disabled:opacity-40 active:scale-95 transition-all"
              >
                {busy ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                Reindex
              </button>
              <button
                onClick={() => onDelete(doc.id)}
                disabled={busy}
                className="flex items-center justify-center gap-1.5 rounded-xl border border-red-200 px-4 py-2.5 text-sm font-semibold text-(--danger) hover:bg-(--danger-light) disabled:opacity-40 active:scale-95 transition-all"
              >
                <Trash2 size={14} />
                Delete
              </button>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
