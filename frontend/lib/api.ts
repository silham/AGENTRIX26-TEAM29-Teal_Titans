import { getLanguage } from "./i18n";
import type {
  Case,
  KnowledgeDoc,
  KnowledgeListResponse,
  KnowledgeSearchResponse,
  KnowledgeStats,
  Language,
  RunEvent,
  VoiceTranscribeResponse,
} from "./types";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

// ── Auth helpers ───────────────────────────────────────────────────────────

export interface StoredUser {
  email: string;
  name: string | null;
  role?: "user" | "admin";
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  return Boolean(sessionStorage.getItem("helplk_token"));
}

export function getStoredUser(): StoredUser | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem("helplk_user");
  if (!raw) return null;
  try { return JSON.parse(raw) as StoredUser; } catch { return null; }
}

/**
 * Whether to SHOW admin UI. This is cosmetic only.
 *
 * The real boundary is the `role` claim inside the JWT, enforced by the
 * backend's require_admin dependency. Someone who edits sessionStorage gets the
 * page and a 403 from every call on it. Note there is no middleware.ts and
 * adding one would not help: sessionStorage is never sent to the server, so a
 * server-side gate would first require moving the token into a cookie.
 */
export function isAdmin(): boolean {
  return getStoredUser()?.role === "admin";
}

export function signOut(): void {
  sessionStorage.removeItem("helplk_token");
  sessionStorage.removeItem("helplk_user");
}

export async function signIn(email: string, name?: string): Promise<void> {
  const res = await fetch("/api/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim(), name: name?.trim() || null }),
  });
  if (!res.ok) throw new Error(`Sign in failed: ${res.status}`);
  const data = await res.json() as {
    token: string; email: string; name: string | null; role?: "user" | "admin";
  };
  sessionStorage.setItem("helplk_token", data.token);
  sessionStorage.setItem(
    "helplk_user",
    JSON.stringify({ email: data.email, name: data.name, role: data.role ?? "user" }),
  );
}

// ── Token (internal) ───────────────────────────────────────────────────────

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem("helplk_token");
}

/**
 * Auth + language on every outbound request.
 *
 * X-Language rather than a ?lang= query param because all four fetch paths in
 * this file (request, deleteCase, streamRun, admin.upload) already call this
 * one function — a query param would have to be threaded through each, and a
 * missed one would silently return English.
 */
function authHeaders(): HeadersInit {
  const token = getToken();
  return {
    "X-Language": getLanguage(),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

// Thrown when the backend returns 401 — caller should redirect to /auth
export class AuthError extends Error {
  constructor() { super("401"); this.name = "AuthError"; }
}

// Thrown for other non-2xx responses. `detail` is the backend's own message
// (already localized server-side where applicable, e.g. the guardrail's
// out-of-scope refusal) — callers that want to show it verbatim can, callers
// that don't can keep using `message`/a generic fallback.
export class ApiError extends Error {
  status: number;
  detail?: string;
  constructor(status: number, detail?: string) {
    super(detail ?? `${status}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

const DEFAULT_TIMEOUT_MS = 15_000;
/**
 * Endpoints that may translate on a cold cache need more than the default.
 * The list endpoint deliberately does NOT: it is cache-only server-side and
 * never waits on the translation model.
 */
const TRANSLATING_TIMEOUT_MS = 45_000;

async function request<T>(
  path: string,
  init?: RequestInit,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${BACKEND}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...authHeaders(), ...(init?.headers ?? {}) },
    });
    if (res.status === 401) {
      // Clear stale token so next call goes to auth page
      signOut();
      throw new AuthError();
    }
    if (!res.ok) {
      const body = await res.json().catch(() => null) as { detail?: string } | null;
      throw new ApiError(res.status, body?.detail);
    }
    return res.json() as Promise<T>;
  } finally {
    clearTimeout(timeout);
  }
}

// ── Cases ─────────────────────────────────────────────────────────────────

export const api = {
  createCase: (goal: string, language = "en") =>
    request<Case>("/cases", {
      method: "POST",
      body: JSON.stringify({ goal, language }),
    }),

  listCases: () => request<Case[]>("/cases"),

  getCase: (id: string) =>
    request<Case>(`/cases/${id}`, undefined, TRANSLATING_TIMEOUT_MS),

  // Mark a step done (or undo); backend recomputes locks/progress and returns the case.
  updateStep: (caseId: string, stepId: string, status: "completed" | "pending") =>
    request<Case>(`/cases/${caseId}/steps/${stepId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }, TRANSLATING_TIMEOUT_MS),

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
    answers?: Record<string, unknown>,
  ) => {
    const url = `${BACKEND}/cases/${caseId}/run${resume ? "?resume=true" : ""}`;
    const ctrl = new AbortController();

    (async () => {
      try {
        const res = await fetch(url, {
          method: "POST",
          headers: {
            ...authHeaders(),
            ...(answers ? { "Content-Type": "application/json" } : {}),
          } as Record<string, string>,
          body: answers ? JSON.stringify({ answers }) : undefined,
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

  // ── Requirements ──────────────────────────────────────────────────────
  // We collect no citizen documents: a requirement is satisfied by the citizen
  // saying they hold it, or by finishing a sub-goal plan that obtains it.

  /** "I have it" (confirmed) or undo (missing). Returns the recomputed case. */
  setRequirement: (caseId: string, reqId: string, status: "confirmed" | "missing") =>
    request<Case>(`/cases/${caseId}/requirements/${reqId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }, TRANSLATING_TIMEOUT_MS),

  /** "How to get it?" — start (or reopen) a plan for obtaining this requirement. */
  createSubGoal: (caseId: string, reqId: string) =>
    request<Case>(
      `/cases/${caseId}/requirements/${reqId}/sub-goal`,
      { method: "POST" },
      TRANSLATING_TIMEOUT_MS,
    ),

  // ── Voice input ────────────────────────────────────────────────────────
  // Fallback path only: browsers with native Web Speech API support (Chrome,
  // Edge) transcribe client-side in VoiceInputButton and never call this.
  // Used by Safari/iOS and any browser without SpeechRecognition, so every
  // supported language still has a voice-input path.
  //
  // Raw fetch, not request<T>: request<T> force-sets Content-Type to
  // application/json, which would destroy the multipart boundary.
  transcribeVoice: async (audio: Blob, language: Language): Promise<VoiceTranscribeResponse> => {
    const fd = new FormData();
    const ext = audio.type.includes("mp4") ? "mp4" : audio.type.includes("wav") ? "wav" : "webm";
    fd.append("file", audio, `voice.${ext}`);
    fd.append("language", language);
    const res = await fetch(`${BACKEND}/voice/transcribe`, {
      method: "POST",
      headers: authHeaders() as Record<string, string>,
      body: fd,
    });
    if (res.status === 401) { signOut(); throw new AuthError(); }
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error((body as { detail?: string }).detail ?? `Transcription failed (${res.status})`);
    }
    return body as VoiceTranscribeResponse;
  },

  // ── Admin knowledge base ──────────────────────────────────────────────
  // Every call here 403s for non-admins; the UI gate is cosmetic (see isAdmin).
  admin: {
    listKnowledge: () => request<KnowledgeListResponse>("/admin/knowledge"),

    stats: () => request<KnowledgeStats>("/admin/knowledge/stats"),

    reindex: (id: string) =>
      request<KnowledgeDoc>(`/admin/knowledge/${id}/reindex`, { method: "POST" }),

    remove: (id: string) =>
      request<{ id: string; deleted: boolean; chunks_removed: number }>(
        `/admin/knowledge/${id}`,
        { method: "DELETE" },
      ),

    search: (q: string, k = 8) =>
      request<KnowledgeSearchResponse>(
        `/admin/search?q=${encodeURIComponent(q)}&k=${k}`,
      ),

    // Raw fetch, not request<T>: request<T> force-sets Content-Type to
    // application/json, which would destroy the multipart boundary.
    upload: async (file: File, meta: { title?: string; sourceUrl?: string }) => {
      const fd = new FormData();
      fd.append("file", file);
      if (meta.title)     fd.append("title", meta.title);
      if (meta.sourceUrl) fd.append("source_url", meta.sourceUrl);
      const res = await fetch(`${BACKEND}/admin/knowledge`, {
        method: "POST",
        headers: authHeaders() as Record<string, string>,
        body: fd,
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error((body as { detail?: string }).detail ?? `Upload failed (${res.status})`);
      }
      return body as KnowledgeDoc;
    },
  },
};
