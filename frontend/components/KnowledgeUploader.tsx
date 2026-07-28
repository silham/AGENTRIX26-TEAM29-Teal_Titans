"use client";

import { useRef, useState } from "react";
import { motion } from "framer-motion";
import { Upload, Loader2, AlertCircle, FileUp } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";

// Mirrors extract.EXT_KIND on the backend, which is the real allowlist.
const ACCEPT = ".pdf,.txt,.md,.markdown,.docx,.png,.jpg,.jpeg,.webp,.tif,.tiff,.bmp";
// Mirrors MAX_KNOWLEDGE_UPLOAD_MB. The server enforces it; this only saves the
// user a round trip for an obviously oversized file.
const MAX_MB = 20;

interface Props {
  onUploaded: () => void;
}

export default function KnowledgeUploader({ onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [title, setTitle]       = useState("");
  const [sourceUrl, setSource]  = useState("");
  const [busy, setBusy]         = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError]       = useState("");

  async function upload(files: FileList | null) {
    if (!files?.length) return;
    setError("");
    setBusy(true);
    try {
      for (const file of Array.from(files)) {
        if (file.size > MAX_MB * 1024 * 1024) {
          throw new Error(`${file.name} is larger than ${MAX_MB} MB.`);
        }
        // Title/source describe one specific document, so they are only applied
        // to a single-file upload; the backend falls back to the filename.
        const single = files.length === 1;
        await api.admin.upload(file, {
          title: single ? title.trim() : "",
          sourceUrl: single ? sourceUrl.trim() : "",
        });
      }
      setTitle("");
      setSource("");
      if (inputRef.current) inputRef.current.value = "";
      onUploaded();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-2xl border border-(--border) bg-white p-4">
      <div className="mb-3 grid gap-2 sm:grid-cols-2">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Title (e.g. Pension Circular 2024)"
          className="rounded-xl border border-(--border) px-3 py-2.5 text-sm outline-none focus:border-(--primary)"
        />
        <input
          value={sourceUrl}
          onChange={(e) => setSource(e.target.value)}
          placeholder="Official source URL (recommended)"
          className="rounded-xl border border-(--border) px-3 py-2.5 text-sm outline-none focus:border-(--primary)"
        />
      </div>
      <p className="mb-3 text-xs text-(--muted-fg)">
        A source URL makes every citation from this document clickable for citizens.
      </p>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          void upload(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors",
          dragging
            ? "border-(--primary) bg-(--primary-light)"
            : "border-(--border) hover:border-(--primary) hover:bg-(--surface)",
        )}
      >
        {busy ? (
          <>
            <Loader2 size={32} className="mb-2 animate-spin text-(--primary)" />
            <p className="text-sm font-semibold text-(--foreground)">Uploading…</p>
          </>
        ) : (
          <>
            <FileUp size={32} className="mb-2 text-(--muted-fg)" />
            <p className="text-sm font-semibold text-(--foreground)">
              Drop government documents here, or click to browse
            </p>
            <p className="mt-1 text-xs text-(--muted-fg)">
              PDF, DOCX, TXT, MD or a scan/photo · up to {MAX_MB} MB
            </p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => void upload(e.target.files)}
        />
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-3 flex items-start gap-2 rounded-xl border border-red-200 bg-(--danger-light) p-3"
        >
          <AlertCircle size={16} className="mt-0.5 shrink-0 text-(--danger)" />
          <p className="text-sm text-(--danger)">{error}</p>
        </motion.div>
      )}

      <p className="mt-3 flex items-center gap-1.5 text-xs text-(--muted-fg)">
        <Upload size={12} />
        Indexing runs in the background — the table below updates as it finishes.
      </p>
    </div>
  );
}
