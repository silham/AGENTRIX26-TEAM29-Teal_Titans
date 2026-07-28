# HelpLK AI — Agentic Citizen Services Copilot for Sri Lanka

> **Build decisions are finalized in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).**
> Sections 14 and 26 below reflect the locked stack; the plan file is the
> authoritative build spec (architecture, data model, task order).

## 1. Project Overview

**HelpLK AI** is an Agentic AI + RAG powered citizen services assistant designed to simplify Sri Lankan government documentation and public service procedures.

Many Sri Lankan citizens struggle with government documentation processes because instructions are scattered across public websites, PDFs, circulars, forms, and office notices. Even when information is technically available in the public domain, it is often difficult for citizens to understand:

* Which documents are required
* Which form should be filled first
* Which government office to visit
* Which steps must be completed before another step
* Whether they are eligible for a service
* What to do when a document is missing
* How to continue a process after a delay

**HelpLK AI** solves this by acting as a **stateful AI case manager** for citizens. Instead of only answering questions, it understands the citizen’s goal, retrieves verified information using RAG, plans the required steps, checks dependencies, validates documents, generates personalized checklists, and tracks the user’s progress.

Core idea:

> ChatGPT answers questions. HelpLK AI executes government procedures.

---

## 2. Problem Statement

Government documentation procedures in Sri Lanka are often complex, paper-heavy, and difficult for ordinary citizens to navigate.

Although instructions are available on public government websites, they are not always:

* Simple
* Personalized
* Updated in one place
* Available in the citizen’s preferred language
* Organized as step-by-step workflows
* Easy to understand for first-time applicants

Citizens frequently face issues such as:

* Not knowing where to start
* Visiting the wrong office
* Missing required documents
* Filling forms incorrectly
* Doing steps in the wrong order
* Misunderstanding eligibility requirements
* Depending on brokers or unofficial advice
* Losing time due to repeated government office visits

This creates frustration for citizens and unnecessary workload for government staff.

---

## 3. Proposed Solution

**HelpLK AI** is a **Government Procedure Copilot** that helps citizens complete government services from start to finish.

The citizen does not need to know the exact department, form name, or procedure name. They can simply describe their situation in natural language.

Example:

> “I lost my NIC and I need to apply for a passport.”

HelpLK AI reasons through the process:

1. Passport application requires a valid NIC.
2. The citizen’s NIC is lost.
3. Therefore, duplicate NIC recovery must happen first.
4. Duplicate NIC may require a police report, birth certificate, and other supporting documents.
5. Passport application should be unlocked only after the NIC requirement is satisfied.
6. The system creates an ordered workflow and tracks progress.

The output is not just a text answer. It is a personalized, stateful citizen service workflow.

---

## 4. Product Positioning

**HelpLK AI** is not a generic chatbot.

It is a citizen procedure execution layer that combines:

* Agentic AI
* Retrieval-Augmented Generation
* Government-specific workflows
* Document understanding
* Case memory
* Personalized eligibility checks
* Procedure dependency graphs
* Multilingual guidance

Positioning statement:

> HelpLK AI is Sri Lanka’s agentic citizen services copilot that guides people from confusion to completion across government documentation procedures.

---

## 5. Why This Is Agentic AI

A basic RAG chatbot follows this pattern:

```text
User question
↓
Retrieve relevant documents
↓
Generate answer
```

HelpLK AI follows an agentic workflow:

```text
Citizen goal
↓
Planner Agent
↓
RAG Knowledge Agent
↓
Dependency Agent
↓
Eligibility Agent
↓
Document Verification Agent
↓
Form Assistant Agent
↓
Checklist Agent
↓
Reminder Agent
↓
Citizen Dashboard
```

HelpLK AI is agentic because it:

* Understands a citizen’s goal
* Breaks the goal into smaller actions
* Retrieves verified government information
* Checks dependencies between services
* Decides the correct order of steps
* Tracks the citizen’s case over time
* Verifies uploaded documents
* Handles missing documents
* Suggests alternative routes
* Provides the next best action
* Maintains a persistent workflow state

---

## 6. Why Not Just ChatGPT or Gemini?

ChatGPT and Gemini are general-purpose language models. They can explain government procedures, but they are not designed to operate as government-grade workflow systems.

HelpLK AI adds a structured, reliable, auditable, government-specific execution layer.

| ChatGPT / Gemini                | HelpLK AI                                      |
| ------------------------------- | ---------------------------------------------- |
| General-purpose assistant       | Government-specific citizen services copilot   |
| Mostly stateless conversation   | Stateful citizen case management               |
| Gives explanations              | Creates executable workflows                   |
| May hallucinate                 | Uses official-source RAG and rule validation   |
| No document tracking            | Tracks uploaded and missing documents          |
| No dependency management        | Understands prerequisite procedures            |
| No audit trail                  | Provides source citations and decision logs    |
| No government integration layer | Designed for future government API integration |

Core answer for evaluators:

> We are not competing with ChatGPT or Gemini. HelpLK AI uses LLMs as one component inside a governed, rule-based, multi-agent system designed specifically for citizen services.

Stronger one-liner:

> ChatGPT answers questions. HelpLK AI manages the citizen journey.

---

## 7. Target Users

### Primary Users

* Sri Lankan citizens applying for government documents
* First-time applicants
* Rural citizens with limited access to guidance
* Elderly citizens
* Students
* Migrant workers
* Small business owners
* Citizens affected by emergencies or lost documents

### Secondary Users

* Government departments
* Divisional Secretariats
* Grama Niladhari offices
* Immigration and Emigration related services
* Registrar-related services
* Local government authorities
* Citizen help desks

---

## 8. Potential Buyer

The primary potential buyer is the **Government of Sri Lanka** or government-affiliated digital service providers.

HelpLK AI can be positioned as:

* A national citizen help desk assistant
* A multilingual government service navigation platform
* A front-office automation tool
* A digital transformation layer for public services
* A citizen support system for e-government portals

Commercial value for government:

* Reduces incomplete applications
* Reduces pressure on physical offices
* Improves citizen satisfaction
* Increases adoption of digital public services
* Provides analytics on citizen pain points
* Standardizes public instructions
* Reduces dependency on unofficial brokers

---

## 9. Main Use Cases

### 9.1 Lost NIC + Passport Application

User says:

> “I lost my NIC and need a passport urgently.”

HelpLK AI responds with a dependency-aware plan:

```text
To apply for a passport, you need a valid NIC.
Since your NIC is lost, you must first complete the duplicate NIC process.

Recommended order:
1. Get a police report for the lost NIC
2. Prepare your birth certificate
3. Get required local certification if applicable
4. Apply for a duplicate NIC
5. Once NIC is received, complete the passport application form
6. Prepare passport-size photographs
7. Book or attend the passport application process
8. Submit application and track status
```

---

### 9.2 Passport Renewal

User says:

> “I want to renew my passport before my Japan trip.”

System checks:

* Existing passport availability
* NIC validity
* Travel date urgency
* Required photographs
* Application form
* Appointment or office visit requirements
* Fast-track possibility, if available

---

### 9.3 Driving License Renewal

User says:

> “My driving license expires next month.”

Generated workflow:

```text
1. Check driving license expiry date
2. Get medical certificate
3. Prepare NIC
4. Fill renewal application
5. Visit relevant RMV/authorized center
6. Pay required fee
7. Track renewal status
```

---

### 9.4 Birth Certificate Copy

User says:

> “I need a copy of my birth certificate.”

HelpLK AI asks only necessary questions:

* District of birth
* Divisional Secretariat
* Date of birth
* Existing certificate number, if available
* Applicant relationship to the person

Then it generates a step-by-step plan.

---

### 9.5 Getting Married

User chooses:

> “Getting married”

System suggests related government procedures:

* Marriage registration
* Birth certificates
* NIC/passport documents
* Witness requirements
* Name change process, if applicable
* Passport update, if applicable
* Bank and legal document updates

---

### 9.6 Starting a Business

User chooses:

> “Starting a business”

System suggests:

* Business name registration
* TIN registration
* Local authority trade license
* EPF/ETF registration if employees exist
* VAT registration if applicable
* Business bank account document preparation

---

### 9.7 Emergency Recovery Mode

User says:

> “I lost all my documents in a flood.”

HelpLK AI prioritizes recovery:

```text
High priority:
1. NIC
2. Birth certificate
3. Passport
4. Land/property documents
5. Insurance documents
6. Education certificates
```

The system creates a recovery roadmap and tracks every replacement procedure.

---

## 10. Core Features

### 10.1 Goal-Based Citizen Assistant

Users can describe their life situation instead of searching by department.

Examples:

```text
“I lost my NIC.”
“I want to go abroad.”
“I am getting married.”
“My father passed away. What documents do I need?”
“I want to start a small shop.”
“My license is expiring.”
```

HelpLK AI maps these goals to relevant government services.

---

### 10.2 Agentic Procedure Planner

The Planner Agent converts a citizen goal into a structured workflow.

Example output:

```json
{
  "goal": "Apply for passport after losing NIC",
  "procedure_plan": [
    {
      "step": 1,
      "title": "Obtain police report",
      "status": "pending"
    },
    {
      "step": 2,
      "title": "Apply for duplicate NIC",
      "status": "pending"
    },
    {
      "step": 3,
      "title": "Prepare passport application",
      "status": "locked",
      "reason": "NIC is required before this step"
    }
  ]
}
```

---

### 10.3 RAG-Based Official Knowledge Retrieval

The RAG layer retrieves information from verified sources such as:

* Government department websites
* Public PDFs
* Application forms
* Circulars
* Gazette notices
* Service pages
* Public instructions

Every important recommendation should be linked to a source.

The system should avoid unsupported answers and clearly state when information is uncertain.

---

### 10.4 Dependency Graph Generator

Many government procedures depend on other procedures.

Example:

```text
Passport application
└── Requires NIC
    └── If NIC is lost
        ├── Police report
        ├── Birth certificate
        └── Duplicate NIC application
```

The Dependency Agent prevents users from doing steps in the wrong order.

---

### 10.5 Eligibility Agent

The Eligibility Agent checks whether the user qualifies for a service.

Possible eligibility factors:

* Age
* Citizenship
* Marital status
* Student status
* Employment status
* Residence district
* Existing document status
* Urgency level
* Previous application status

Example:

```text
You are eligible for a passport application, but your NIC is missing.
You must complete duplicate NIC application first.
```

---

### 10.6 Smart Checklist Generator

HelpLK AI generates a personalized checklist for each case.

Example:

```text
Required documents:
✓ Birth certificate
✓ Police report
✗ NIC
✗ Passport-size photos
✗ Completed application form
```

The checklist updates dynamically as the user uploads documents or completes steps.

---

### 10.7 Document Upload and Validation

Citizens can upload scanned documents or photos.

The Document Verification Agent checks:

* Whether the document type is correct
* Whether the uploaded image is readable
* Whether required fields are visible
* Whether signatures are missing
* Whether photo requirements are violated
* Whether a document appears expired, if applicable

Example output:

```text
Birth certificate: Accepted
NIC: Missing
Passport photo: Rejected — background may not meet requirement
Application form: Incomplete — signature missing on page 2
```

---

### 10.8 Form Assistant Agent

The Form Assistant Agent helps users understand and complete government forms.

Capabilities:

* Explain difficult fields
* Translate field labels
* Auto-fill known details
* Identify missing sections
* Generate draft filled forms
* Detect incorrect date formats
* Detect unsigned sections

Example:

```text
Field: Permanent Address
Explanation: This should be your official long-term residential address.
```

---

### 10.9 Multilingual Support

HelpLK AI should support:

* Sinhala
* Tamil
* English

The system should be able to:

* Translate instructions
* Explain legal/formal wording simply
* Accept questions in multiple languages
* Provide step-by-step guidance in the citizen’s preferred language

---

### 10.10 Citizen Dashboard

The dashboard shows all active government procedures.

Example:

```text
My Government Tasks

Passport Application
Progress: 60%
Next step: Apply for duplicate NIC

Driving License Renewal
Progress: 20%
Next step: Get medical certificate

Birth Certificate Copy
Progress: 100%
Status: Completed
```

---

### 10.11 Progress Memory and Case Management

HelpLK AI maintains a stateful case record.

Example:

```json
{
  "case_id": "CASE-001",
  "citizen_goal": "Passport after lost NIC",
  "completed_steps": ["Police report"],
  "current_step": "Apply for duplicate NIC",
  "blocked_steps": ["Passport application"],
  "missing_documents": ["NIC", "passport photos"]
}
```

The citizen can return later and say:

> “Continue my passport process.”

The system remembers the progress.

---

### 10.12 Reminder Agent

The Reminder Agent helps users stay on track.

Examples:

```text
Your appointment is tomorrow.
Your license expires in 15 days.
You still need to upload your police report.
Your application step has been inactive for 7 days.
```

---

### 10.13 What-If Simulation Agent

Citizens often ask alternative questions.

Examples:

```text
Can I apply without my NIC?
What if my birth certificate is missing?
Can I use my old passport instead?
```

The What-If Agent simulates alternative paths.

Example output:

```text
You cannot complete the standard passport process without a valid NIC.

Alternative path:
1. Apply for duplicate NIC
2. Receive or verify NIC
3. Continue passport application
```

---

### 10.14 Life Event Mode

Instead of selecting a government department, citizens can select a life event.

Life events:

* Getting married
* Having a child
* Starting a business
* Going abroad
* Losing documents
* Death of family member
* Moving residence
* Buying land
* Applying for university
* Applying for employment
* Retiring

Each life event triggers a bundle of related government procedures.

---

## 11. Agent Architecture

### 11.1 Planner Agent

Purpose:

Convert the user’s goal into a structured plan.

Responsibilities:

* Understand user intent
* Identify relevant services
* Break the goal into steps
* Decide which agents to call next
* Generate an initial workflow

Input:

```json
{
  "user_goal": "I lost my NIC and need a passport"
}
```

Output:

```json
{
  "detected_services": ["Duplicate NIC", "Passport Application"],
  "workflow_required": true,
  "next_agent": "Dependency Agent"
}
```

---

### 11.2 RAG Knowledge Agent

Purpose:

Retrieve verified information from official sources.

Responsibilities:

* Search indexed government documents
* Retrieve relevant instructions
* Extract requirements
* Return source citations
* Flag outdated or conflicting information

Output:

```json
{
  "service": "Passport Application",
  "requirements": ["NIC", "Birth Certificate", "Photographs", "Application Form"],
  "sources": [
    {
      "title": "Official passport instruction page",
      "url": "source_url"
    }
  ]
}
```

---

### 11.3 Dependency Agent

Purpose:

Identify prerequisite procedures.

Responsibilities:

* Build dependency trees
* Lock unavailable steps
* Explain why a step is blocked
* Suggest prerequisite workflows

Example:

```json
{
  "blocked_step": "Passport Application",
  "reason": "Valid NIC is required",
  "required_first": "Duplicate NIC Application"
}
```

---

### 11.4 Eligibility Agent

Purpose:

Check whether a user qualifies for a service.

Responsibilities:

* Ask minimal required questions
* Check eligibility rules
* Identify special cases
* Warn users about blockers

---

### 11.5 Document Verification Agent

Purpose:

Check uploaded documents.

Responsibilities:

* Detect document type
* Extract visible text using OCR/vision
* Check required fields
* Detect missing signatures
* Detect unreadable uploads
* Update document checklist

---

### 11.6 Form Assistant Agent

Purpose:

Help citizens understand and complete forms.

Responsibilities:

* Explain form fields
* Translate form sections
* Validate completed forms
* Generate draft form data
* Detect incomplete fields

---

### 11.7 Checklist Agent

Purpose:

Generate and update the citizen’s checklist.

Responsibilities:

* Convert procedure requirements into tasks
* Mark completed and missing items
* Update progress percentage
* Show next best action

---

### 11.8 Reminder Agent

Purpose:

Keep the citizen on track.

Responsibilities:

* Remind about appointments
* Remind about expiry dates
* Remind about incomplete steps
* Notify users about pending documents

---

### 11.9 Audit and Trust Agent

Purpose:

Make AI decisions explainable and government-safe.

Responsibilities:

* Store source citations
* Log why each recommendation was made
* Identify unsupported claims
* Flag low-confidence answers
* Provide transparent decision history

---

## 12. System Workflow

```text
1. User enters a goal
   Example: “I lost my NIC and need a passport.”

2. Planner Agent detects services
   Services: Duplicate NIC, Passport Application

3. RAG Knowledge Agent retrieves official instructions
   Sources: Government PDFs, forms, department pages

4. Dependency Agent builds process graph
   Passport depends on NIC

5. Eligibility Agent checks user-specific conditions
   Example: citizen status, age, document availability

6. Checklist Agent creates personalized tasks
   Tasks are ordered and status-based

7. Document Verification Agent checks uploaded files
   Missing, accepted, rejected, or incomplete

8. Form Agent helps complete forms
   Explains fields and validates missing sections

9. Reminder Agent tracks progress
   Alerts citizen about next steps

10. Dashboard shows case status
   User can continue later
```

---

## 13. Suggested MVP for 12-Hour Hackathon

The MVP should focus on a visually impressive and clearly agentic demo rather than full production integration.

### Must-Have MVP Features

1. Natural language goal input
2. Multi-agent processing animation
3. RAG-style answer with source placeholders
4. Dependency-based workflow generation
5. Personalized checklist
6. Document upload mock validation
7. Citizen dashboard
8. Case progress memory
9. Sinhala/Tamil/English language selector
10. “Why this step?” explanation with source citation

### Recommended Demo Scenario

Use this as the main demo:

> “I lost my NIC and need to apply for a passport.”

This scenario is powerful because it shows:

* Multiple government services
* Dependency reasoning
* Missing document handling
* Ordered workflow generation
* Personalized checklist
* Agentic planning

---

## 14. Tech Stack (FINALIZED — all free tier)

### Frontend

* Next.js (App Router)
* Tailwind CSS + shadcn/ui
* Framer Motion for the live agent-processing animation (driven by real SSE events)

### Backend

* **FastAPI (Python)** — hosts the agent graph and RAG

### Agent Framework

* **LangGraph** — stateful graph with a **Postgres checkpointer** and
  `interrupt()` for human-in-the-loop, which is how long/resumable sessions work

### RAG (Hybrid)

* **LlamaIndex** + **pgvector**
* JSON rules layer (`backend/data/procedures/*.json`) for deterministic
  dependency/eligibility/locking
* Embedding layer over ~15–20 real SL gov pages/PDFs for free-text answers + citations

### LLMs (free)

* **Groq (Llama 3.3 70B)** — planner, dependency, eligibility, form, what-if (JSON mode)
* **Gemini 1.5 Flash** — document vision, Sinhala/Tamil/English, `text-embedding-004`
* **Tesseract** — zero-quota OCR fallback

### Database / Storage

* **PostgreSQL + pgvector** (Supabase or Neon free tier) — NextAuth tables,
  domain state, LangGraph checkpoints, and embeddings in one data plane
* Private storage bucket (Supabase Storage / Cloudflare R2) for uploaded documents

### Authentication

* **NextAuth (Auth.js)** in the Next.js layer — magic link (Resend) or Google OAuth
* Next.js mints a short-lived HS256 JWT (shared `AUTH_SECRET`) that FastAPI
  verifies; all backend queries scoped by `user_id`

---

## 15. Suggested Data Models

### Citizen Case

```json
{
  "case_id": "CASE-001",
  "user_id": "USER-001",
  "goal": "I lost my NIC and need a passport",
  "status": "in_progress",
  "progress": 45,
  "current_step": "Apply for duplicate NIC",
  "created_at": "2026-06-20T10:00:00"
}
```

### Procedure Step

```json
{
  "step_id": "STEP-001",
  "case_id": "CASE-001",
  "title": "Get police report",
  "description": "Obtain a police report for the lost NIC.",
  "status": "completed",
  "depends_on": [],
  "source": "official_source_url"
}
```

### Document Item

```json
{
  "document_id": "DOC-001",
  "case_id": "CASE-001",
  "name": "Birth Certificate",
  "status": "accepted",
  "issues": []
}
```

### Agent Log

```json
{
  "agent": "Dependency Agent",
  "decision": "Passport application is blocked until NIC is available.",
  "reason": "NIC is listed as a required identity document.",
  "source": "official_source_url",
  "confidence": 0.91
}
```

---

## 16. UI Screens for Hackathon Demo

### Screen 1 — Landing Page

Title:

```text
HelpLK AI
Your Agentic Citizen Services Copilot
```

Subtitle:

```text
Describe your government service need. HelpLK AI will plan, verify, and guide you step by step.
```

Input examples:

```text
I lost my NIC and need a passport.
I want to renew my driving license.
I need a copy of my birth certificate.
I am starting a small business.
```

---

### Screen 2 — Goal Input

User types:

```text
I lost my NIC and need to apply for a passport.
```

Button:

```text
Start My Procedure
```

---

### Screen 3 — Agent Processing View

Show animated agent cards:

```text
Planner Agent — Understanding your goal
Knowledge Agent — Searching verified sources
Dependency Agent — Checking prerequisite steps
Eligibility Agent — Personalizing requirements
Checklist Agent — Creating your action plan
```

This screen is important because it visually proves the project is agentic.

---

### Screen 4 — Generated Workflow

Display:

```text
Your Procedure Plan

1. Get police report for lost NIC
2. Prepare birth certificate
3. Apply for duplicate NIC
4. Wait for NIC confirmation
5. Complete passport application form
6. Prepare passport photos
7. Submit passport application
```

Locked step example:

```text
Passport application is locked until duplicate NIC step is completed.
```

---

### Screen 5 — Document Checklist

Display:

```text
Documents

✓ Birth Certificate
✓ Police Report
✗ NIC
⚠ Passport Photo — needs verification
✗ Completed Passport Form
```

---

### Screen 6 — Document Upload Validation

Mock upload result:

```text
Uploaded: Passport_Form.pdf

Status: Incomplete

Issues found:
- Signature missing on page 2
- Date field is empty
- NIC field cannot be completed because NIC is missing
```

---

### Screen 7 — Citizen Dashboard

Display:

```text
My Cases

Passport After Lost NIC
Progress: 45%
Current step: Apply for duplicate NIC
Next action: Visit relevant office with police report and birth certificate

Driving License Renewal
Progress: 20%
Current step: Get medical certificate
```

---

### Screen 8 — Explainability Panel

Display:

```text
Why is passport application locked?

Because a valid NIC is required for identity verification.
Since your NIC is marked as lost, HelpLK AI recommends completing the duplicate NIC process first.

Source:
Official government instruction reference
```

---

## 17. 2-Minute Demo Video Storyboard

### 0:00–0:10 — Problem

Show text:

```text
Government procedures are confusing.
Forms, documents, offices, prerequisites — citizens often do not know where to start.
```

Show a simple UI with scattered forms/documents.

---

### 0:10–0:25 — Product Introduction

Show landing page.

Text:

```text
Introducing HelpLK AI
Sri Lanka’s Agentic Citizen Services Copilot
```

---

### 0:25–0:40 — User Goal

User types:

```text
I lost my NIC and need to apply for a passport.
```

Click:

```text
Start My Procedure
```

---

### 0:40–1:00 — Agentic Processing

Show agent cards activating one by one:

```text
Planner Agent
RAG Knowledge Agent
Dependency Agent
Eligibility Agent
Document Agent
Checklist Agent
```

Overlay text:

```text
HelpLK AI does not just answer.
It plans, verifies, and manages the full procedure.
```

---

### 1:00–1:20 — Workflow Output

Show generated plan:

```text
1. Get police report
2. Prepare birth certificate
3. Apply for duplicate NIC
4. Continue passport application
5. Submit documents
```

Show locked passport step:

```text
Locked until NIC is recovered.
```

---

### 1:20–1:40 — Document Validation

Show upload screen.

Result:

```text
Birth Certificate: Accepted
Police Report: Accepted
NIC: Missing
Passport Form: Signature missing
```

---

### 1:40–1:55 — Dashboard

Show citizen dashboard:

```text
Passport Case: 45% complete
Next action: Apply for duplicate NIC
Reminder: Upload passport photo
```

---

### 1:55–2:00 — Closing

Show final tagline:

```text
HelpLK AI
From confusion to completion.
```

Alternative tagline:

```text
Government services, guided step by step.
```

---

## 18. Hackathon Pitch

### 30-Second Pitch

HelpLK AI is an Agentic AI citizen services copilot for Sri Lanka. Citizens often struggle with government documentation because instructions are scattered, complex, and difficult to follow in the correct order. HelpLK AI allows a citizen to simply describe their goal, such as “I lost my NIC and need a passport.” A team of AI agents then retrieves verified government information, checks dependencies, creates a personalized workflow, validates documents, and tracks progress through a citizen dashboard. Unlike ChatGPT, HelpLK AI is not just a Q&A bot. It is a stateful, auditable government procedure engine.

---

### 60-Second Pitch

Sri Lankan citizens lose time and money because government documentation procedures are difficult to understand. Even when instructions are available online, citizens often do not know which documents are required, which form comes first, or what to do when something is missing.

HelpLK AI solves this problem using Agentic AI and RAG. The citizen describes a goal in natural language, such as “I lost my NIC and need a passport.” HelpLK AI uses multiple specialized agents: a Planner Agent, Knowledge Agent, Dependency Agent, Eligibility Agent, Document Verification Agent, and Reminder Agent. Together, they retrieve verified public information, build the correct procedure order, generate a personalized checklist, validate uploaded documents, and track the citizen’s case over time.

This is not a generic chatbot. ChatGPT can answer a question, but HelpLK AI manages the full citizen journey from confusion to completion. The potential buyer is the government, because the platform can reduce incomplete applications, improve citizen satisfaction, and support Sri Lanka’s digital government transformation.

---

## 19. Judge Q&A Preparation

### Question: Why do we need this when ChatGPT or Gemini already exists?

Answer:

ChatGPT and Gemini are general-purpose language models. HelpLK AI is a government-specific workflow engine. It uses LLMs, but adds agent orchestration, official-source RAG, dependency checking, document validation, case memory, audit logs, and citizen progress tracking.

ChatGPT answers a question. HelpLK AI manages a procedure.

---

### Question: How do you prevent hallucinations?

Answer:

HelpLK AI uses a RAG-first approach. Important recommendations are generated from indexed official sources, and every major step is linked to a citation. The system also has an Audit and Trust Agent that flags unsupported claims, low-confidence answers, and conflicting information.

---

### Question: Is this commercially viable?

Answer:

Yes. The direct buyer can be the government or a government digital transformation partner. The system can reduce incomplete applications, reduce help desk pressure, improve service accessibility, and provide analytics on where citizens struggle most.

---

### Question: What makes this agentic?

Answer:

The system has multiple agents with specialized responsibilities. It plans, retrieves, checks eligibility, identifies dependencies, validates documents, updates progress, and recommends the next best action. It is not a single chatbot response. It is a stateful, multi-step, tool-using workflow.

---

### Question: Can this integrate with real government systems?

Answer:

Yes. The current hackathon version can use public documents and mock workflows. In production, it can integrate with appointment systems, document verification APIs, citizen identity systems, payment systems, and government service portals.

---

## 20. Non-Goals for Hackathon MVP

The 12-hour MVP should not attempt to build every real integration.

Avoid spending too much time on:

* Real government login
* Real payment processing
* Real appointment booking
* Full legal accuracy for every department
* Production-grade OCR
* Full Sinhala/Tamil perfection
* Large-scale user authentication

Focus on proving:

* Agentic planning
* RAG-based guidance
* Dependency reasoning
* Document checklist
* Case dashboard
* Strong user experience

---

## 21. Success Metrics

### Citizen Impact Metrics

* Reduction in incomplete applications
* Reduction in repeated office visits
* Time saved per citizen
* Increase in successful first-time submissions
* Language accessibility improvement

### Government Impact Metrics

* Lower help desk workload
* Better service adoption
* Reduced manual clarification requests
* Common citizen issue analytics
* Standardized public guidance

### Product Metrics

* Number of active citizen cases
* Procedure completion rate
* Document validation accuracy
* User satisfaction score
* Average time to complete a process

---

## 22. Future Enhancements

* Real government API integrations
* Appointment booking
* SMS/WhatsApp reminders
* Voice assistant in Sinhala and Tamil
* Offline mode for rural areas
* Kiosk mode for Divisional Secretariats
* Broker-fraud prevention warnings
* Government officer dashboard
* Analytics for policy makers
* Citizen document vault
* Automated form filling
* Secure digital identity integration

---

## 23. Security, Privacy, and Trust

HelpLK AI may handle sensitive citizen documents, so security is critical.

Required principles:

* Store only necessary information
* Encrypt uploaded documents
* Allow users to delete documents
* Use role-based access control
* Maintain audit logs
* Avoid exposing private citizen data to unauthorized users
* Clearly separate verified facts from AI-generated suggestions
* Show source citations for procedural guidance

---

## 24. Final Taglines

Primary tagline:

```text
HelpLK AI — From confusion to completion.
```

Alternative taglines:

```text
Your agentic guide for government services.
```

```text
Government procedures, simplified step by step.
```

```text
Sri Lanka’s citizen services copilot.
```

```text
Describe your need. Let agents plan the procedure.
```

---

## 25. Repository Instruction for AI Coding Agents

When implementing this project, prioritize a polished hackathon demo.

Build the application around the main demo flow:

```text
User goal:
“I lost my NIC and need to apply for a passport.”
```

The application should clearly demonstrate:

1. Natural language input
2. Multi-agent reasoning
3. RAG-based government knowledge retrieval
4. Dependency-aware workflow generation
5. Personalized checklist
6. Mock document validation
7. Citizen dashboard
8. Explainability and citations

Do not implement unnecessary production complexity. Use mock data where needed, but structure the code so real government data sources and APIs can be integrated later.

The final demo should make evaluators immediately understand that HelpLK AI is not a chatbot. It is an agentic citizen service workflow platform.

---

## 26. Finalized Architecture (Build Decisions)

These supersede the "suggested" framing earlier in this document. Full detail,
data model, and ordered task list live in
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

* **Topology:** Next.js (Vercel) ⇄ FastAPI (Python) ⇄ Postgres + pgvector.
* **Agentic core:** LangGraph graph (Planner → RAG → Dependency → Eligibility →
  Checklist → Document Verify → Form → Reminder; Audit/Trust cross-cutting),
  streaming node updates over SSE.
* **State retention:** two layers — durable domain tables
  (`cases/steps/documents/agent_logs`) as the source of truth, plus a LangGraph
  **Postgres checkpointer** (`thread_id = case_id`) so a run can pause on an
  upload/answer and resume later. This is the "continue my process days later" story.
* **Auth:** NextAuth owns identity; FastAPI trusts a shared-secret JWT and scopes
  every query by `user_id`. No second login system.
* **RAG:** hybrid — JSON rules for reliable dependency/eligibility, embeddings for
  citations and narrative answers; UI always separates verified fact (with source)
  from AI suggestion.
* **Data safety:** private bucket behind authorized endpoints, per-user scoping
  (optional RLS), delete endpoints, PII minimization, audit logs.
* **Everything free tier:** Groq, Gemini, Supabase/Neon, Vercel, Resend.

---

## 27. Multilingual (Sinhala / Tamil / English) — the invariant

> **The graph, the database and the rules layer are English-only.
> Citizen input is normalised to English once, on the way IN.
> Citizen-facing text is translated once, at the API boundary, on the way OUT.**

Read this before touching anything under `app/i18n/`, `app/graph/`, or the
language handling in the frontend.

**Why English is canonical.** Persisting translated steps would make switching
language a destructive write: `replace_steps` is DELETE+INSERT, so a re-run
drops manually completed steps. Under this design, switching language is a pure
read-path change — zero writes. It also keeps the English RAG corpus, the
English-tuned score floor and the English keyword fallback working untouched.

**Three rules that are load-bearing, not stylistic:**

1. **`options[].value` and `field` are machine keys. NEVER translate them.**
   `_check_rule` compares them with exact `==` against English values from the
   procedure JSON. A translated value makes an eligible citizen read as
   ineligible — a silent denial with no error anywhere. Only `question` and
   `label` are translated. See `tests/test_m8_i18n_eligibility.py`.
2. **Deep-copy before translating anything from graph state.** The paused-run
   payload aliases the LangGraph checkpoint's own objects; mutating them leaves
   Sinhala questions in state, which are then replayed into English-only prompts
   on resume.
3. **A citizen's own goal is never translated.** `Case.goal` holds their exact
   words; `Case.goal_en` holds the English the graph consumes. Only
   `goal_source == "generated"` text (machine-composed sub-goals) is translated.

**Where things live**

| Concern | Module |
|---|---|
| Input → English (script, transliteration, mixed) | `app/i18n/understand.py` |
| English → si/ta, with a persistent cache | `app/i18n/translator.py` |
| Which response fields get translated | `app/i18n/localize.py` |
| Official government terminology | `app/i18n/glossary.py` |
| Per-request render language (`X-Language`) | `app/i18n/deps.py` |
| UI chrome strings | `frontend/lib/i18n/{en,si,ta}.ts` |

**Operational notes**

* Warm the cache and produce a review file:
  `python -m scripts.seed_translations` then `--export reviewed.tsv`.
  Corrected rows import back as `source='human'` and are never overwritten.
* Bump `translator.PROMPT_VERSION` when the prompt or glossary changes
  materially — it is part of the cache key, so old machine output is superseded.
* `GET /cases` is **cache-only** and must stay that way: a cold-cache model call
  there would exceed the client's request timeout and read as a server error.
* `/admin` is intentionally English-only (staff-only surface).
* Adding a key to `frontend/lib/i18n/en.ts` breaks the `si.ts`/`ta.ts` compile
  until it is translated. That is the parity check — do not weaken it.
