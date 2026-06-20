import type { Case, RunEvent } from "./types";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

// Demo token stored in sessionStorage (set by /api/demo-token)
function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem("helplk_token");
}

function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BACKEND}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(init?.headers ?? {}) },
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

// ── Cases ─────────────────────────────────────────────────────────────────

export const api = {
  createCase: (goal: string, language = "en") =>
    request<Case>("/cases", {
      method: "POST",
      body: JSON.stringify({ goal, language }),
    }),

  listCases: () => request<Case[]>("/cases"),

  getCase: (id: string) => request<Case>(`/cases/${id}`),

  deleteCase: (id: string) =>
    fetch(`${BACKEND}/cases/${id}`, {
      method: "DELETE",
      headers: authHeaders() as Record<string, string>,
    }),

  // ── SSE stream ──────────────────────────────────────────────────────────
  streamRun: (
    caseId: string,
    onEvent: (e: RunEvent) => void,
    onDone: () => void,
    onError: (msg: string) => void,
    resume = false,
  ) => {
    const url = `${BACKEND}/cases/${caseId}/run${resume ? "?resume=true" : ""}`;
    const ctrl = new AbortController();

    (async () => {
      try {
        const res = await fetch(url, {
          method: "POST",
          headers: { ...authHeaders() } as Record<string, string>,
          signal: ctrl.signal,
        });
        if (!res.ok) { onError(`${res.status}`); return; }
        const reader = res.body!.getReader();
        const dec = new TextDecoder();
        let buf = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += dec.decode(value, { stream: true });
          const parts = buf.split("\n\n");
          buf = parts.pop() ?? "";
          for (const part of parts) {
            const line = part.replace(/^data: /, "").trim();
            if (!line) continue;
            try {
              const evt = JSON.parse(line) as RunEvent;
              onEvent(evt);
              if (evt.agent === "system" && evt.status === "completed") onDone();
              if (evt.agent === "system" && evt.status === "error") onError(evt.message ?? "error");
            } catch { /* ignore malformed */ }
          }
        }
        onDone();
      } catch (e: unknown) {
        if ((e as Error).name !== "AbortError") onError(String(e));
      }
    })();

    return () => ctrl.abort();
  },

  // ── Documents ─────────────────────────────────────────────────────────
  uploadDocument: (caseId: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("case_id", caseId);
    return fetch(`${BACKEND}/documents`, {
      method: "POST",
      headers: authHeaders() as Record<string, string>,
      body: fd,
    }).then((r) => r.json());
  },

  deleteDocument: (docId: string) =>
    fetch(`${BACKEND}/documents/${docId}`, {
      method: "DELETE",
      headers: authHeaders() as Record<string, string>,
    }),
};
