# PERFORMai-360: System Architecture Specification

**Project Title:** PERFORMai-360: AI-Driven Bias-Aware 360° Performance Evaluation for Software Engineering Teams
**Document Status:** Phase 11 Final Documentation, Verification, and Demonstration Readiness Completed
**Target Environment:** macOS Local Development, Docker Compose, Python 3.14+, Node.js v26+

---

## 1. Architectural Vision and Core Principles

PERFORMai-360 is an evidence-grounded performance review intelligence system. It assists software engineering managers and organizations in synthesizing 360-degree feedback, detecting potential evidence gaps and review imbalances, and drafting transparent review reports.

The architecture is governed by five non-negotiable principles:

1. **Human-in-the-Loop Decision Support:** The system is strictly an assistance tool. Consequential decisions (promotions, compensation, termination) must never be made autonomously. Reports require human review, editing, and explicit approval before finalization.
2. **Evidence Traceability:** Every factual finding in an AI-generated draft must be linked to verifiable source evidence identifiers (`evidence_ids`). If evidence is insufficient, the system explicitly reports an evidence gap rather than hallucinating details.
3. **Deterministic Bias & Review-Quality Auditing:** Imbalances (recency bias, lack of stakeholder diversity, ungrounded claims, vague language) are flagged by transparent, explainable audit rules to prompt human reflection.
4. **Data Isolation & Least Privilege:** Role-based access control (RBAC) is strictly enforced server-side. Employees, peers, managers, and administrators only access records permitted by organizational policy.
5. **Provider-Agnostic AI Layer:** The multi-agent workflow operates behind a provider-neutral abstraction, supporting offline mock providers for development and testing without paid API dependencies.

---

## 2. High-Level System Architecture

```mermaid
graph TD
    subgraph ClientLayer["Client Layer (Browser)"]
        UI["Next.js App Router (TypeScript + Tailwind CSS + shadcn/ui)"]
    end

    subgraph APILayer["Backend API Layer (FastAPI)"]
        API["FastAPI REST API (/api/v1)"]
        AuthMiddleware["Auth & RBAC Middleware"]
        Routers["Routers (Auth, Cycles, Feedback, Goals, Evidence, Reports, Audit)"]
        ServiceLayer["Business Logic & Validation Layer (Pydantic v2)"]
    end

    subgraph WorkflowLayer["Multi-Agent Orchestration (LangGraph)"]
        Orchestrator["Workflow State Machine"]
        EvidenceAgent["1. Evidence Retrieval Agent"]
        AnalysisAgent["2. Feedback Analysis Agent"]
        AuditAgent["3. Bias & Evidence Auditor"]
        SynthesisAgent["4. Review Synthesis Agent"]
        ApprovalPause["5. Human Approval Pause Node"]
    end

    subgraph AILayer["AI Abstraction Layer"]
        Adapter["LLM Provider Adapter"]
        MockProvider["Mock Provider (Deterministic/Test)"]
        ExternalLLM["External LLM (OpenAI / Anthropic / Ollama)"]
    end

    subgraph DataLayer["Persistence & Storage Layer"]
        PG[(PostgreSQL Database)]
        DocStorage["Local Evidence Storage (uploads/)"]
    end

    UI -->|HTTPS / JSON API| API
    API --> AuthMiddleware
    AuthMiddleware --> Routers
    Routers --> ServiceLayer
    ServiceLayer --> PG
    ServiceLayer --> DocStorage
    ServiceLayer -->|Trigger Run| Orchestrator

    Orchestrator --> EvidenceAgent
    EvidenceAgent --> AnalysisAgent
    AnalysisAgent --> AuditAgent
    AuditAgent --> SynthesisAgent
    SynthesisAgent --> ApprovalPause

    EvidenceAgent -.->|Scoped Retrieval| PG
    AnalysisAgent --> Adapter
    AuditAgent --> Adapter
    SynthesisAgent --> Adapter

    Adapter --> MockProvider
    Adapter --> ExternalLLM
```

---

## 3. Technology Stack and Rationale

| Layer | Component | Selection | Rationale |
| :--- | :--- | :--- | :--- |
| **Frontend** | Framework | Next.js (App Router, React 19 / TypeScript) | Type-safe, component-driven, responsive UI for review workflows |
| **Frontend** | Styling / UI | Tailwind CSS + shadcn/ui | Clean, accessible design system with customizable components |
| **Frontend** | Visualizations | Recharts | Clear visual indicators for review coverage, date distribution, and metrics |
| **Backend** | Framework | Python + FastAPI | High-performance asynchronous API, native Pydantic schema validation, clean modular design |
| **Backend** | ORM & Migrations | SQLAlchemy 2.0 (asyncio) + Alembic | Mature relational mapping, transactional integrity, and versioned schema migrations |
| **Database** | Primary Store | PostgreSQL 16+ | Strong ACID compliance, relational integrity, JSON support, and future-ready for pgvector |
| **Orchestration** | Multi-Agent Engine | LangGraph | Deterministic state machine supporting branching, validation nodes, and human approval pauses |
| **AI Integration** | Provider Adapter | Provider-Neutral Adapter | Decouples business logic from external LLM vendors; supports offline mock provider |
| **Testing** | Suite | pytest (backend), Vitest (frontend), Playwright (E2E) | Comprehensive multi-tier automated testing strategy |
| **Local Services** | Containerization | Docker Compose | Reproducible local PostgreSQL and supporting service environments |

---

## 4. Multi-Agent Workflow Architecture

The multi-agent evaluation pipeline is organized as an explicit, observable state graph in LangGraph. Each stage has typed Pydantic input and output contracts:

```mermaid
stateDiagram-v2
    [*] --> ValidateInputs: Request AI Analysis
    ValidateInputs --> RetrieveEvidence: Permissions & Inputs OK
    ValidateInputs --> Failed: Input Validation Failed

    RetrieveEvidence --> AnalyzeFeedback: Scoped Evidence Packaged
    AnalyzeFeedback --> RunAudit: Candidate Findings Extracted

    state RunAudit {
        [*] --> CheckEvidenceCoverage
        CheckEvidenceCoverage --> CheckRecencyConcentration
        CheckRecencyConcentration --> CheckStakeholderCoverage
        CheckStakeholderCoverage --> CheckVagueClaims
        CheckVagueClaims --> CheckContradictions
        CheckContradictions --> [*]
    }

    RunAudit --> SynthesizeReport: Audit Flags & Quality Notes Generated
    SynthesizeReport --> ValidateDraft: Draft Report Assembled with Source IDs

    ValidateDraft --> PauseForApproval: Schemas & Source IDs Valid
    ValidateDraft --> Failed: Malformed Draft / Invalid IDs

    PauseForApproval --> ManagerReview: Human Reviewer Inspects Draft
    ManagerReview --> Approved: Manager Approves Draft
    ManagerReview --> ChangesRequested: Manager Requests Revision / More Evidence
    ManagerReview --> SynthesizeReport: Re-run with Updated Evidence

    Approved --> Finalized: Create Immutable Approved Version & Audit Log
    Finalized --> [*]
    Failed --> [*]
```

### Specialist Agent Responsibilities:
1. **Evidence Retrieval Agent:** Queries and filters authorized inputs (self-assessment, peer feedback, manager notes, goals, uploaded evidence) restricted to the employee, review cycle, and requesting user's scope.
2. **Feedback Analysis Agent:** Extracts candidate strengths, achievements, growth opportunities, and goal progress, tagging each finding with source evidence references.
3. **Bias & Evidence Auditor:** Executes deterministic rules and heuristics:
   - *Evidence Coverage:* Identifies ungrounded or unsupported evaluative claims.
   - *Recency Concentration:* Detects disproportionate reliance on events at the end of the review window.
   - *Stakeholder Coverage:* Assesses feedback balance across peers, self, and manager.
   - *Vague / Absolute Language:* Flags generalizations ("always", "never", "poor attitude") lacking concrete work context.
   - *Contradictory Feedback:* Identifies conflicting reviewer perspectives for human reconciliation.
4. **Review Synthesis Agent:** Formats validated findings, audit flags, goal progress, and limitations into a structured draft report.
5. **Human Approval Pause:** Halts automated execution until an authorized human manager reviews, edits, and explicitly decides (Approve, Reject, Request Changes).

---

## 5. Core Domain Entities & Relational Design

```mermaid
erDiagram
    USER ||--o{ TEAM_MEMBERSHIP : has
    TEAM ||--o{ TEAM_MEMBERSHIP : contains
    TEAM ||--o{ REVIEW_CYCLE : scopes
    USER ||--o{ REVIEW_CYCLE : "subject of"
    USER ||--o{ REVIEW_CYCLE : "managed by"

    REVIEW_CYCLE ||--o{ FEEDBACK : contains
    REVIEW_CYCLE ||--o{ GOAL : tracks
    REVIEW_CYCLE ||--o{ EVIDENCE : attaches
    REVIEW_CYCLE ||--o{ WORKFLOW_RUN : executes
    REVIEW_CYCLE ||--o{ FINDING : extracts
    REVIEW_CYCLE ||--o{ BIAS_FLAG : flags
    REVIEW_CYCLE ||--o{ REVIEW_REPORT : produces

    REVIEW_REPORT ||--o{ APPROVAL : receives
    USER ||--o{ APPROVAL : signs
    USER ||--o{ AUDIT_EVENT : triggers

    USER {
        uuid id PK
        string email
        string full_name
        string role
        boolean is_active
        timestamp created_at
    }

    REVIEW_CYCLE {
        uuid id PK
        uuid employee_id FK
        uuid manager_id FK
        date period_start
        date period_end
        string status
        string template_id
    }

    FEEDBACK {
        uuid id PK
        uuid cycle_id FK
        uuid author_id FK
        string feedback_type
        text content
        string visibility
    }

    EVIDENCE {
        uuid id PK
        uuid cycle_id FK
        string source_type
        string title
        string storage_path
        date source_date
        jsonb metadata
    }

    REVIEW_REPORT {
        uuid id PK
        uuid cycle_id FK
        int version_number
        jsonb structured_content
        string status
        uuid generated_by_run_id FK
    }

    REPORT_VERSION {
        uuid id PK
        uuid report_id FK
        uuid cycle_id FK
        int version_number
        string status
        string changed_section
        string change_summary
        uuid author_id FK
        string author_role
        boolean is_ai_generated
        jsonb structured_content
        timestamp created_at
    }

    APPROVAL {
        uuid id PK
        uuid report_id FK
        uuid version_id FK
        int version_number
        uuid reviewer_id FK
        string decision
        text comments
        timestamp timestamp
    }

    AUDIT_EVENT {
        uuid id PK
        uuid actor_id FK
        string action
        string resource_type
        string resource_id
        timestamp timestamp
        jsonb metadata
    }
```

---

## 6. Security, Privacy, and Audit Controls

- **Role-Based Access Control (RBAC):** Backend endpoints authenticate callers via JWT/header principals and verify role permissions (`Employee`, `Peer Reviewer`, `Manager`, `Administrator`).
- **Data Isolation:** All database queries are filtered by tenant/employee and cycle scope. Peer feedback visibility policies are enforced at the service layer.
- **Report Version Invariance & Concurrency Control:** Saved draft edits enforce optimistic concurrency (`base_version_number`). Historical snapshots in `report_versions` are immutable. Once a version snapshot is approved, subsequent edits advance to a new version in `draft` status without overwriting the signed-off historical snapshot.
- **Deterministic Diff Engine:** Pure algorithmic diff calculation (unified text diffs and structured list deltas) guarantees transparent, non-hallucinated version comparisons.
- **Audit Logging:** Critical events (logins, evidence uploads, analysis triggers, section edits, approvals, revision requests) generate immutable, append-only `AuditEvent` records. Sensitive credentials or confidential prompts are never logged.
- **Untrusted File Parsing:** Uploaded documents (PDF, DOCX, TXT, CSV) are treated as untrusted data. Files undergo strict MIME validation, file size limits (default 10 MB), and safe parsing in isolation.
- **Synthetic Data Baseline:** Test fixtures and demo scenarios strictly utilize synthetic identities to guarantee privacy during demonstrations.

---

## 7. Analytics, Report Exports, and Accessibility Architecture (Phase 9)

### Real-Time SQL Analytics Engine
- **Direct Aggregations:** Computes metrics (overview, lifecycle distribution, evidence sources, bias rules, activity trends) strictly via SQLAlchemy PostgreSQL aggregation queries without N+1 loops.
- **Strict Completion Rate:** Mathematically defined as `finalized_cycles / total_cycles` with explicit numerator and denominator exposed.
- **Hierarchical Access Scoping:** Queries dynamically filter by `cycle.owner_id == viewer_id` (manager scope) or `cycle.employee_id == viewer_id` (employee scope) ensuring zero cross-tenant or cross-employee information disclosure.

### Multi-Format Export Architecture (PDF & DOCX)
- **Separation of Concerns:** Export rendering logic is isolated inside `app/services/report_export_service.py`, keeping API route handlers lean.
- **PDF Generation (`ReportLab`):** Uses a two-pass `NumberedCanvas` to calculate total pages dynamically ("Page X of Y"), structured story flow, metadata grid, strengths/growth callouts with citation IDs, and approval/draft decision stamps.
- **Word Generation (`python-docx`):** Produces styled `.docx` files with formatted headings, callout tables, bulleted strengths/growth areas, and approval decision banners.
- **Version Pinning:** Supports exporting historical snapshots (`?version_number=X`) directly from `report_versions` to guarantee that exported artifacts match the exact signed-off review state.
- **Safe In-Memory Streaming:** Output is generated into `io.BytesIO` streams, eliminating temporary disk artifacts and directory traversal risks.

### Accessibility Standards (WCAG 2.2 AA)
- **Visual Contrast & Semantic Landmarks:** Proper HTML5 landmark roles (`<header>`, `<main>`, `<section aria-labelledby="...">`), high contrast color palette, and logical focus indicators.
- **Alternative Tabular Representations:** Recharts visualizations provide a user-toggleable semantic `<table>` alternative (`showDataTables`) with `<caption>`, `<th scope="col">`, and high-contrast row styling for screen readers and assistive technology.
- **Live Status Announcements:** ARIA live regions (`role="status"`, `aria-live="polite"`) communicate loading, error, and refresh events.

---

---

## 8. Security Architecture, Hardening, and End-to-End Validation (Phase 10)

### Server-Side Principal Resolution & Role Precedence
- **Authoritative Ingestion (`app/core/security.py`):** Centralized caller resolution where authenticated request headers (`X-Viewer-Id`, `X-Viewer-Role`) strictly override query parameters. An untrusted caller passing `?viewer_role=admin` while holding an employee header is strictly resolved to `employee`.
- **Role Verification:** Critical lifecycle state changes (approvals, revisions, cancellations, workflows) execute mandatory `verify_manager_or_admin()` checks before invoking service transactions.

### Confidential Information Masking & Data Leakage Prevention
- **Managerial Notes Protection:** The JSON responses for `GET /api/v1/reports/{id}`, `GET /api/v1/review-cycles/{id}/report`, `GET /api/v1/reports/{id}/versions/{version_number}`, and `GET /api/v1/reports/{id}/compare` dynamically sanitize and strip confidential `reviewer_notes` whenever accessed by employees.
- **Diff Redaction:** Comparison diffs between historical versions redact lines, bullet summaries, and keys mentioning reviewer notes for non-managerial callers.

### Privilege Loophole Closure: Self-Approval Prevention
- **Separation of Subject & Evaluator:** In hierarchical workflows, a user who is a manager in the organization cannot approve, request revisions on, or cancel their own performance review. Both `WorkflowService._authorize_and_get_cycle` and `ReportGovernanceService._verify_access` prioritize subject employee verification (`cycle.employee_id == viewer_id`) before role checks, raising HTTP 403 Forbidden.

### Automated End-to-End Testing (Playwright)
- **Production Validation:** Headless Chromium automated suite (`apps/web/e2e/e2e-journeys.spec.ts`) executing against the production Next.js build on port 3001. Validates application navigation, Recharts analytics, accessible data table toggles, report governance controls, and LangGraph workflow pipeline state with 100% pass rate.

---

## 9. Demonstration Architecture and Verification Framework (Phase 11)

### Multi-Tier Automated Verification Harness
- **Backend Quality Gates (pytest + Ruff):** 144 unit, integration, and security tests executing against PostgreSQL 16 using `NullPool` with automatic transaction rollback. Zero state bleed or test fixture pollution. Fast, deterministic execution (<3.5s total runtime).
- **Database Schema Invariance (`Alembic`):** `alembic check` verifies that declarative SQLAlchemy 2.0 ORM models match migration history (`8884fdc13f66` through `8e1543950fd6 (head)`) with zero untracked drift.
- **Frontend Quality Gates (Next.js + ESLint):** Zero ESLint warnings, TypeScript type safety, static route prerendering, and optimized production bundle compilation via Turbopack.
- **End-to-End Browser Automation (Playwright):** 5 headless Chromium journeys executing against production build on isolated port 3001, verifying navigation, analytics dashboards, accessible WCAG tables, report governance, and multi-agent workflow state.

### Repeatable Synthetic Demonstration Architecture
- **Synthetic Personas & Data Isolation:** All demonstration workflows utilize strictly synthetic user profiles (Carol Manager, Alice Employee, Bob Peer, Dave Manager, and System Admin). Real employee data and external credentials are systematically excluded.
- **Repeatable Step-by-Step Flow:** Fully documented in [`docs/DEMO_GUIDE.md`](file:///Users/kaustubhkadam/Desktop/PERFORMai-360-Fresh/docs/DEMO_GUIDE.md) covering the 11 key operational stages from cycle initiation to branded PDF/DOCX report exports.
- **Security Boundary Demonstrations:** Dedicated demonstration paths for cross-employee isolation (404 Not Found), manager self-approval rejection (403 Forbidden), and role spoofing prevention via server-side header precedence.

### Decision-Support Governance & AI Safety Boundaries
- **Strict Human Agency:** The platform functions as an evidence-grounded decision-support tool. Autonomous employment, compensation, promotion, and termination decisions are structurally prohibited.
- **Source Citation Enforcement:** All extracted performance findings must link to valid source `evidence_ids`. Cross-employee or ungrounded claims are stripped and flagged with explicit system limitations.
- **Immutable Governance Trail:** Approvals, revision requests, and section modifications generate immutable, append-only `AuditEvent` records and versioned snapshots in `report_versions`.

---

## 10. Phased Implementation Strategy

Development is executed sequentially across twelve controlled phases:
- **Phase 0:** Repository and Planning Baseline *(Completed)*
- **Phase 1:** Application Skeleton & Local Developer Environment *(Completed)*
- **Phase 2:** Core Database Models & Persistence *(Completed)*
- **Phase 3:** Core Review Workflow (Cycles, Feedback, Goals, Evidence) *(Completed)*
- **Phase 4:** Evidence Processing & Scoped Retrieval *(Completed)*
- **Phase 5:** Single-Pass AI Analysis & Grounded Performance Insights *(Completed)*
- **Phase 6:** Deterministic Bias & Evidence-Quality Audit Engine *(Completed)*
- **Phase 7:** LangGraph Multi-Agent Orchestration *(Completed)*
- **Phase 8:** Human Approval, Report Versioning, and Governance *(Completed)*
- **Phase 9:** Dashboard Polish, Accessibility, and Export *(Completed)*
- **Phase 10:** Comprehensive Testing, Security, and Quality Review *(Completed)*
- **Phase 11:** Final Documentation, Evaluation Metrics, and Demonstration Readiness *(Completed)*
