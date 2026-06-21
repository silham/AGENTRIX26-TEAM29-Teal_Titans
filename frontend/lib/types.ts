// ── Backend response types (mirror backend/app/schemas/) ─────────────────

export type StepStatus = "pending" | "active" | "completed" | "locked" | "skipped";
export type DocStatus  = "missing" | "accepted" | "rejected" | "incomplete" | "needs_verification";
export type CaseStatus = "in_progress" | "completed" | "cancelled";
export type Language   = "en" | "si" | "ta";

export interface Step {
  id: string;
  ord: number;
  title: string;
  description?: string;
  status: StepStatus;
  depends_on: string[];
  source_url?: string;
  reason?: string;
}

export interface Document {
  id: string;
  name: string;
  type?: string;
  status: DocStatus;
  issues: string[];
}

export interface Case {
  id: string;
  user_id: string;
  goal: string;
  status: CaseStatus;
  progress: number;
  current_step_id?: string;
  language: Language;
  created_at: string;
  updated_at: string;
  steps: Step[];
}

export interface AgentLog {
  agent: string;
  decision: string;
  reason?: string;
  source_url?: string;
  confidence?: number;
}

// ── SSE event shape (mirrors backend/app/schemas/run.py) ─────────────────

export type AgentStatus = "started" | "completed" | "error";

export interface RunEvent {
  agent: string;
  status: AgentStatus;
  message?: string;
  payload?: Record<string, unknown>;
}

// ── UI state ──────────────────────────────────────────────────────────────

export interface AgentState {
  name: string;
  label: string;
  description: string;
  status: "idle" | "running" | "done" | "error";
  payload?: Record<string, unknown>;
}

// Plain-English labels visible to citizens (no technical "Agent" naming)
export const AGENTS: Omit<AgentState, "status">[] = [
  { name: "planner",     label: "Reading your request",            description: "Understanding what you need help with" },
  { name: "knowledge",   label: "Checking government information", description: "Finding the correct official rules and steps" },
  { name: "dependency",  label: "Finding the right order",         description: "Checking which steps must come before others" },
  { name: "eligibility", label: "Checking your situation",         description: "Making sure the steps match your personal needs" },
  { name: "checklist",   label: "Building your plan",              description: "Creating your personal step-by-step guide" },
  { name: "document",    label: "Listing your documents",          description: "Finding out which papers you need to bring" },
  { name: "form",        label: "Checking the forms",              description: "Looking at what forms need to be filled" },
  { name: "reminder",    label: "Finishing up",                    description: "Your plan is almost ready" },
];

// ── i18n ─────────────────────────────────────────────────────────────────

export const LANG_LABELS: Record<Language, string> = {
  en: "English",
  si: "සිංහල",
  ta: "தமிழ்",
};

export const DEMO_GOALS = [
  "I lost my NIC and need to apply for a passport",
  "I want to renew my driving licence",
  "I need a copy of my birth certificate",
  "I lost all my documents in a flood",
  "I am starting a small business",
  "I want to get married",
];
