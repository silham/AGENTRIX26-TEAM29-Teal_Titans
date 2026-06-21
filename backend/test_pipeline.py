"""Quick end-to-end pipeline test — no DB, no auth, no server needed."""
import sys, os, json
sys.path.insert(0, ".")
os.environ["GROQ_API_KEY"]    = "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"
os.environ["GEMINI_API_KEY"]  = "AQ.Ab8RN6LU7OH_qYhClwqa347F38hUlitMVHGeBSVccvkUyxz3WA"
os.environ["AUTH_SECRET"]     = "change-me-shared-with-nextauth"
os.environ["DATABASE_URL"]    = "postgresql://x"
os.environ["FRONTEND_ORIGIN"] = "http://localhost:3000"

GOAL = "I want to buy a car"

def sep(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ─── 1. PLANNER ───────────────────────────────────────────────────────────────
from app.graph.nodes.planner import _keyword_plan, _generate_custom_plan

kp = _keyword_plan(GOAL)
sep("1. PLANNER")
print("Keyword services  :", kp["detected_services"])

steps, reqs = _generate_custom_plan(GOAL)
print("Groq service name :", steps[0].get("_service_name") if steps else "n/a")
print("Groq office       :", steps[0].get("_office") if steps else "n/a")
print("\nRequirements from Groq:")
for r in reqs:
    print(f"  • {r}")
print("\nSteps from Groq:")
for i, s in enumerate(steps, 1):
    print(f"  {i}. {s['title']}")
    if s.get("description"):
        print(f"     {s['description'][:90]}")

# Build state to thread through nodes
state = {
    "case_id": "TEST-001",
    "user_id": "USER-001",
    "goal": GOAL,
    "language": "en",
    "detected_services": ["custom_procedure"],
    "custom_steps": steps,
    "custom_requirements": reqs,
    "intent": {
        "primary_goal": GOAL, "urgency": "medium",
        "missing": [], "lost": [], "have": [],
    },
    "documents": [],
    "facts": {},
    "logs": [],
    "messages": [],
}

# ─── 2. KNOWLEDGE ─────────────────────────────────────────────────────────────
from app.graph.nodes.knowledge import knowledge

sep("2. KNOWLEDGE")
k_out = knowledge(state)
print("Requirements surfaced:")
for r in k_out.get("requirements", []):
    print(f"  • {r}")
print("\nCitations / sources:")
for c in k_out.get("citations", []):
    print(f"  [{c['title']}]")
    print(f"   {c['source_url']}")
    if c.get("snippet"):
        print(f"   snippet: {c['snippet'][:80]}...")
state.update(k_out)

# ─── 3. DEPENDENCY ────────────────────────────────────────────────────────────
from app.graph.nodes.dependency import dependency

sep("3. DEPENDENCY")
d_out = dependency(state)
dg  = d_out.get("dependency_graph", {})
svc = dg.get("services", {}).get("custom_procedure", {})
print("Service status :", svc.get("status"))
print("Locked         :", dg.get("locked"))
print("Reason         :", svc.get("reason"))
state.update(d_out)

# ─── 4. ELIGIBILITY ───────────────────────────────────────────────────────────
from app.graph.nodes.eligibility import eligibility

sep("4. ELIGIBILITY")
e_out = eligibility(state)
print("Overall verdict:", e_out.get("eligibility", {}).get("overall"))
print("Questions to ask citizen:")
for q in e_out.get("questions", []):
    print(f"  ? {q}")
state.update(e_out)

# ─── 5. CHECKLIST ─────────────────────────────────────────────────────────────
from app.graph.nodes.checklist import compose_checklist

sep("5. CHECKLIST  (what the citizen sees)")
items, progress = compose_checklist(
    dg,
    e_out.get("eligibility", {}),
    [],
    {"custom_procedure": steps},
)
print(f"Progress: {progress}%   |   Total steps: {len(items)}\n")
icons = {"pending": "[ ]", "active": "[>]", "completed": "[x]", "locked": "[L]"}
for it in items:
    icon = icons.get(it["status"], "?")
    print(f"  {icon}  {it['status']:9}  {it['title']}")

sep("DONE")
