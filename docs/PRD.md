# PERFORMai-360 --- Product Requirements Document (PRD)

**Project title:** PERFORMai-360: AI-Driven Bias-Aware 360° Performance
Evaluation for Software Engineering Teams\
**Document type:** Product Requirements Document (PRD) and phased
implementation specification\
**Version:** 1.0\
**Status:** Baseline for development\
**Intended implementation environment:** Antigravity IDE, macOS, GitHub\
**Primary users:** Employees, peers/reviewers, managers,
HR/administrators\
**Recommended stack:** Next.js + TypeScript, Tailwind CSS + shadcn/ui,
FastAPI + Python, PostgreSQL, SQLAlchemy, Alembic, LangGraph, an
interchangeable LLM provider, pytest, Playwright, Docker Compose

------------------------------------------------------------------------

## 1. Executive Summary

PERFORMai-360 is a web-based performance-review intelligence system for
software engineering teams. It helps organizations prepare more
evidence-grounded, balanced, explainable, and reviewable 360-degree
performance evaluations.

The system collects employee self-assessments, peer feedback, manager
feedback, goals, meeting notes, and project evidence. It organizes this
information by employee and review period, extracts relevant findings,
checks for missing or unsupported evidence, flags possible review
imbalances, and drafts a structured report. An authorized human reviewer
must edit or approve the draft before it is finalized.

The system is an **assistance and decision-support tool**, not an
autonomous employment decision-maker. It must not independently decide
promotions, compensation, termination, hiring, or other consequential
employment outcomes. A flag means "review this issue"; it does not prove
that a reviewer is biased or that a claim is false.

The first release will be a controlled, locally runnable MVP using
synthetic/demo data. External integrations such as GitHub and Jira are
optional extensions and must not block delivery of the MVP.

## 2. Problem Statement

Performance reviews can become inconsistent or unfair when they rely on
incomplete evidence, subjective language, one person's perspective, or
events that occurred near the end of a review period. Feedback can also
be vague, contradictory, or disconnected from stated goals and actual
work.

PERFORMai-360 addresses these issues by: - Bringing multiple feedback
sources into one review workflow. - Linking report findings to traceable
source evidence. - Flagging possible recency effects, unsupported
claims, missing perspectives, vague statements, and conflicting
feedback. - Synthesizing evidence into a structured draft. - Keeping the
authorized human reviewer in control of the final report. - Recording
review versions, approval decisions, and important system actions.

### 2.1 Core problem statement

**Build a Bias-Aware 360° Performance Review Intelligence System that
ingests employee self-assessments, manager/peer feedback, goals, project
outcomes, and meeting notes; synthesizes evidence into structured review
reports; flags potential bias and evidence gaps; coordinates the process
through a controlled multi-agent workflow; and requires human approval
before report finalization while preserving privacy, governance, and
auditability.**

## 3. Product Vision and Goals

### 3.1 Vision

Help software engineering teams prepare performance reviews that are
clearer, more evidence-grounded, balanced across the review period,
transparent about uncertainty, and accountable to human judgment.

### 3.2 Goals

1.  Provide a complete review workflow from review-cycle creation to
    human-approved report.
2.  Support 360-degree feedback from employee self-assessments, peers,
    managers, goals, and project evidence.
3.  Make AI-generated claims traceable to source records.
4.  Detect and explain potential evidence and review-quality issues.
5.  Orchestrate specialized AI tasks through an observable, stateful
    workflow.
6.  Protect employee information through access control, data
    minimization, secure configuration, and audit logs.
7.  Run locally on a Mac during development and provide repeatable setup
    instructions.
8.  Make the MVP testable and demonstrable with synthetic data and
    documented evaluation results.

### 3.3 Non-goals

The MVP will not: - Make autonomous employment decisions or assign
binding promotion/termination outcomes. - Claim to prove a person's
intent, prejudice, or discrimination from text alone. - Treat commits,
lines of code, pull-request counts, ticket counts, or sentiment as
standalone measures of employee performance. - Scrape private systems or
connect to employer systems without explicit authorization. - Require a
paid LLM API to run the basic application. - Require Kubernetes,
microservices, or cloud deployment. - Promise legally compliant
employment decisions merely because the software has bias checks. -
Infer protected characteristics from names, photos, writing style, or
other indirect signals.

## 4. Users, Roles, and Permissions

The application must enforce permissions in the backend. Hiding a button
in the frontend is not sufficient access control.

### 4.1 Employee

-   View their own profile and authorized review cycles.
-   Submit and edit their self-assessment while the cycle is open.
-   View permitted feedback/report content according to configured
    organizational policy.
-   Add comments or acknowledge a finalized review if enabled.
-   Never access another employee's confidential feedback unless
    explicitly authorized.

### 4.2 Peer Reviewer

-   Submit feedback only for assigned review requests.
-   Edit their own submission until the relevant deadline or cycle lock.
-   See only the feedback forms and status information needed to
    complete their task.
-   Not view other reviewers' confidential submissions by default.

### 4.3 Manager / Review Owner

-   View employees and review cycles they are authorized to manage.
-   Request peer feedback and review self-assessments.
-   Add manager feedback, goals, and authorized evidence.
-   Generate a draft report, inspect evidence, respond to audit flags,
    edit the report, and approve or return it for revision.
-   Cannot bypass mandatory approval-state rules.

### 4.4 Administrator

-   Manage users, roles, teams, review templates, and application
    configuration.
-   Access audit records according to policy.
-   Does not automatically receive unrestricted access to all
    confidential feedback; sensitive access must be policy-based and
    auditable.

### 4.5 Development/demo mode

-   Seed a clearly marked synthetic dataset.
-   Provide documented demo accounts only for local development.
-   Never use real employee data in committed seed files.
-   Disable or strongly guard demo shortcuts outside development mode.

## 5. Product Scope and Release Priorities

### P0 --- Required for MVP

-   Authentication and role-based authorization.
-   Employee/team management.
-   Review-cycle creation and status management.
-   Self-assessment, peer feedback, and manager feedback.
-   Goal management and evidence upload/reference management.
-   Structured review report generation.
-   Source references for factual findings.
-   At least four deterministic audit checks: evidence missing, recency
    concentration, stakeholder coverage imbalance, and vague/unsupported
    claims.
-   Controlled multi-agent workflow with observable stages.
-   Human review, editing, approval, rejection, and revision.
-   Audit log and version history.
-   Synthetic seed data.
-   Automated tests, setup documentation, and local run instructions.

### P1 --- Valuable after core MVP

-   PDF/DOCX report export.
-   Semantic evidence retrieval using PostgreSQL and optional pgvector.
-   Additional contradictory-feedback checks.
-   Review dashboard and analytics.
-   Configurable review templates.
-   Email notifications in a development-safe mode.

### P2 --- Optional extensions

-   GitHub pull-request and repository evidence integration.
-   Jira issue/project evidence integration.
-   Local LLM provider.
-   Cross-cycle trend analysis.
-   Carefully governed aggregate fairness analysis.
-   Cloud deployment and organizational SSO.

The team must not start P1/P2 work until all P0 acceptance criteria
pass.

## 6. Key User Journeys

### Journey A --- Create and complete a review

1.  A manager signs in.
2.  The manager selects an employee and creates a review cycle with
    start/end dates.
3.  The manager configures goals and invites/assigns reviewers.
4.  The employee submits a self-assessment.
5.  Assigned peers submit feedback.
6.  The manager adds their assessment and authorized project evidence.
7.  The system validates required inputs and reports missing
    information.
8.  The manager requests AI analysis.

### Journey B --- Generate and audit a report

1.  The workflow retrieves records the requesting manager is authorized
    to access.
2.  The evidence agent builds a source-linked evidence set.
3.  The analysis agent extracts candidate findings.
4.  Deterministic checks and the bias-audit stage inspect evidence
    coverage, date concentration, unsupported claims, and stakeholder
    balance.
5.  The synthesis stage creates a draft with strengths, growth areas,
    goal progress, impact, limitations, and evidence references.
6.  The manager reviews every flagged issue and can open its source
    records.
7.  The manager edits the report, requests regeneration, or returns it
    for more evidence.
8.  The manager approves the report.
9.  The system records the approver, time, version, and decision.

### Journey C --- Handle insufficient evidence

1.  The system detects missing or low-quality evidence.
2.  It marks relevant conclusions as uncertain or omits them.
3.  It presents a clear evidence-gap notice.
4.  It asks for additional authorized evidence or human review.
5.  It must not invent details or interpret missing data as poor
    performance.

## 7. Functional Requirements

Priority notation: **P0** = required for MVP; **P1** = next release;
**P2** = optional.

### FR-01: Authentication and authorization --- P0

-   Users can sign in and sign out securely.
-   Passwords must be stored using a suitable password-hashing
    algorithm; plaintext passwords are prohibited.
-   Every protected backend endpoint checks the user's identity and
    permissions.
-   Roles include employee, peer reviewer, manager, and administrator.
-   Unauthorized requests return appropriate HTTP status codes without
    leaking confidential data.
-   Authentication secrets and API keys must be stored in environment
    variables, never committed to Git.
-   Provide secure session or token handling, including expiry and
    logout behavior.

### FR-02: User, team, and employee management --- P0

-   Administrators can create, edit, deactivate, and list users.
-   Users can be associated with teams and authorized managers.
-   Employee profiles contain only necessary work-related fields.
-   Team and employee lists are filtered according to the current user's
    permissions.
-   Deactivation must not silently erase records needed for an
    authorized audit trail.

### FR-03: Review-cycle management --- P0

-   Managers can create a cycle with employee, period, template, due
    dates, and status.
-   Supported states: `draft`, `open`, `collecting_feedback`,
    `analysis_pending`, `draft_report`, `changes_requested`, `approved`,
    `finalized`, `archived`.
-   State transitions must be validated by the backend.
-   Finalized cycles cannot be silently overwritten; edits require a new
    report version or an authorized reopen operation.
-   The application must show missing required inputs and workflow
    status.

### FR-04: Feedback collection --- P0

-   Support self-assessment, peer feedback, and manager feedback.
-   Store author, subject employee, review cycle, category, text,
    created/updated timestamps, and visibility policy.
-   Feedback forms should use clear prompts tied to work-related
    behaviors and examples.
-   Validate required fields and length limits.
-   Preserve a record of meaningful edits when needed for auditability.
-   Avoid collecting irrelevant sensitive personal information.

### FR-05: Goals and outcomes --- P0

-   Managers and authorized employees can record goals, measurable
    targets, due dates, status, and outcome notes.
-   Goal status must be explicit: `not_started`, `in_progress`,
    `completed`, `blocked`, or `cancelled`.
-   The system must distinguish a self-reported outcome from a verified
    project record.
-   Goal completion alone must not be treated as a complete measure of
    overall performance.

### FR-06: Evidence management --- P0

-   Authorized users can upload supported documents or enter evidence
    references/notes.
-   Initial supported uploads should include PDF, DOCX, TXT, and CSV
    where appropriate.
-   Validate file type, file size, and content handling; do not trust
    the filename or MIME type alone.
-   Store evidence metadata, uploader, timestamp, source type,
    review-cycle association, and access policy.
-   Each extracted finding must reference one or more evidence IDs where
    applicable.
-   Treat uploaded content as untrusted data and never execute it.
-   Provide a way to remove or supersede incorrectly uploaded evidence
    subject to retention policy.

### FR-07: Evidence retrieval --- P0

-   Retrieve only evidence relevant to the selected employee, review
    period, and requesting user's permissions.
-   Support exact metadata filters before optional semantic retrieval.
-   Return stable evidence IDs and source metadata with excerpts.
-   Do not allow one employee's evidence to leak into another employee's
    report.
-   If evidence is absent or retrieval fails, clearly report the gap
    rather than fabricate a result.

### FR-08: AI feedback analysis --- P0

-   Extract candidate achievements, strengths, growth areas, goal
    progress, impact statements, and development suggestions.
-   Return validated structured output conforming to a defined schema.
-   Separate direct evidence, reviewer opinion, model interpretation,
    and suggested action.
-   Include evidence IDs, dates, uncertainty/limitations, and confidence
    only where meaningfully defined.
-   Do not invent projects, metrics, quotes, dates, or accomplishments.
-   Reject or repair malformed model output with bounded retries; fail
    safely if validation still fails.
-   Record the model/provider and prompt/template version used for each
    run without logging unnecessary confidential content.

### FR-09: Bias and evidence-quality audit --- P0

The system must flag potential issues, not make definitive accusations.

**Checks required for MVP:** 1. **Evidence coverage:** identify key
claims without source references or relevant examples. 2. **Recency
concentration:** compare the dates of feedback/evidence with the review
period and flag a report that relies heavily on a narrow recent window
while earlier evidence exists. 3. **Stakeholder coverage:** show the
number and types of available feedback sources and warn when expected
sources are missing or one source dominates. 4. **Vague or absolute
claims:** flag language such as "always," "never," or "bad attitude"
when not supported by specific work-related examples. 5. **Contradictory
feedback:** identify potentially conflicting claims and present both
source references when feasible.

Each flag must include: - `flag_type` - Plain-language explanation -
Severity/priority (not a judgment of a person's character) - Supporting
source IDs or the reason a source is missing - Suggested reviewer
action - Status: `open`, `acknowledged`, `resolved`, or
`not_applicable` - Optional reviewer comment

Do not treat a missing peer review as evidence that the employee
performed poorly. Do not infer intent or protected traits. Group-level
statistical comparisons are P2 and require appropriate data governance
and sufficient sample sizes.

### FR-10: Multi-agent workflow --- P0

Implement a controlled LangGraph workflow or equivalent explicit state
machine with these logical stages: 1. Input and permission validation.
2. Evidence retrieval. 3. Feedback analysis. 4. Deterministic and
LLM-assisted audit. 5. Report synthesis. 6. Output validation. 7. Human
approval pause. 8. Finalization and audit event.

The first implementation should use four specialist roles: - **Evidence
Retrieval Agent:** finds and packages authorized source records. -
**Feedback Analysis Agent:** extracts candidate findings. - **Bias &
Evidence Auditor:** flags possible bias patterns and evidence gaps. -
**Review Synthesis Agent:** prepares a report draft from validated
findings.

A workflow orchestrator controls sequencing, state, retry limits, and
approval. These can be logical agents implemented as separate
nodes/functions; they do not need to be independent autonomous services.

Requirements: - Define typed input/output schemas for each stage. - Set
timeouts, bounded retries, and clear failure states. - Do not let an
agent directly change permissions, approve reports, or perform
consequential actions. - Treat all retrieved/uploaded text as untrusted
input, not instructions. - Log stage status, duration, and non-sensitive
error metadata. - Allow a failed workflow to be retried safely without
duplicating records. - Persist enough state to inspect the workflow and
resume an approval-paused run.

### FR-11: Report synthesis --- P0

Every draft report should contain: 1. Employee and review-period
details, subject to permissions. 2. Executive summary. 3. Strengths and
contributions. 4. Growth areas. 5. Goal progress. 6. Evidence-backed
impact highlights. 7. Potential bias/evidence-quality flags. 8. Evidence
gaps and limitations. 9. Suggested development goals. 10. Reviewer notes
and approval status.

Each factual claim should reference evidence IDs or be explicitly
labeled as self-reported/opinion/interpretation. Report sections may say
"insufficient evidence to assess" when appropriate. The report must not
conceal unresolved critical evidence gaps.

### FR-12: Human review and approval --- P0

-   A draft report is never automatically finalized.
-   Authorized reviewers can view source evidence for each finding.
-   Reviewers can edit report text, acknowledge or resolve flags,
    request additional evidence, reject the draft, or approve it.
-   Approval records reviewer ID, timestamp, report version, and
    decision.
-   Finalization is blocked if required approval is missing or mandatory
    validation fails.
-   The UI must clearly distinguish AI-generated content from
    human-edited content.
-   Re-running analysis creates a new version and must not silently
    overwrite a human-approved report.

### FR-13: Audit log and versioning --- P0

-   Record important actions: authentication events as appropriate,
    feedback creation/editing, evidence upload/deletion, AI run
    start/completion/failure, report edits, flag decisions, approvals,
    and role changes.
-   Each event should include actor, action, resource type/ID,
    timestamp, and relevant metadata.
-   Do not place passwords, access tokens, or full confidential prompts
    in audit logs.
-   Audit records must be protected from ordinary user modification.
-   Preserve report versions and show which version was approved.

### FR-14: Dashboard and user experience --- P0

-   Provide role-appropriate navigation and dashboards.
-   Show review-cycle status, outstanding feedback tasks, evidence
    completeness, audit flags, and approval status.
-   Use clear loading, empty, success, and error states.
-   Ensure keyboard navigation, readable contrast, labels, and
    responsive layouts.
-   Never rely on color alone to convey severity or status.
-   Provide a source-detail view from report findings and audit flags.

### FR-15: Export and integrations

-   **P1:** Export approved reports to PDF and DOCX.
-   **P2:** Optional GitHub and Jira integrations using least-privilege,
    read-only access where possible.
-   Integrations must be disabled by default until configured.
-   External activity metrics are contextual evidence only and must not
    become automatic employee scores.
-   Document provider permissions, data fields collected, and revocation
    steps.

## 8. Non-Functional Requirements

### NFR-01: Security

-   Enforce authorization server-side for every protected operation.
-   Validate and normalize inputs.
-   Use secure password hashing and protected session/token storage.
-   Use environment variables for secrets and commit only
    `.env.example`.
-   Apply upload limits and safe file parsing.
-   Avoid exposing stack traces or confidential information to end
    users.
-   Include dependency and configuration checks in the development
    workflow.

### NFR-02: Privacy

-   Use synthetic data for demos and automated tests.
-   Collect the minimum required information.
-   Restrict data by employee, review cycle, role, and policy.
-   Document retention and deletion behavior.
-   Avoid logging full feedback or documents unless strictly necessary.
-   Do not send real employee data to an external LLM without explicit
    authorization and an approved data-handling arrangement.
-   Provide a provider abstraction so local or approved models can be
    substituted.

### NFR-03: Reliability

-   Validate all API inputs/outputs.
-   Use database transactions for multi-record state changes.
-   Provide useful error messages and structured internal logging.
-   Fail closed when authorization or required validation fails.
-   Ensure retries are bounded and safe.

### NFR-04: Performance

For the local MVP, establish measurable baselines rather than promising
production-scale performance. Target ordinary non-AI API operations to
respond within 500 ms at the 95th percentile under a small local test
workload, excluding database startup and file processing. AI response
time depends on the selected model/provider and should be measured
separately.

### NFR-05: Maintainability

-   Use clear module boundaries and typed schemas.
-   Keep frontend, backend, database migrations, tests, and
    documentation organized.
-   Pin or constrain dependencies and document supported runtime
    versions.
-   Provide linting, formatting, and tests.
-   Avoid oversized files and duplicated business logic.

### NFR-06: Accessibility and usability

-   Responsive layout for laptop and common tablet sizes.
-   Clear form labels, keyboard support, accessible status text, and
    useful validation messages.
-   Explain bias flags in plain language with actionable next steps.

### NFR-07: Explainability

-   Trace report claims to evidence IDs.
-   Separate evidence from interpretation.
-   Explain why each flag was raised.
-   Record unresolved uncertainty.
-   Provide a path for a human to challenge or correct a finding.

## 9. Recommended Technical Architecture

### 9.1 Stack

  -----------------------------------------------------------------------
  Layer                   Choice                  Purpose
  ----------------------- ----------------------- -----------------------
  Frontend                Next.js App Router,     Web application and
                          React, TypeScript       dashboards

  Styling/UI              Tailwind CSS, shadcn/ui Consistent accessible
                                                  UI

  Charts                  Recharts                Review and workflow
                                                  analytics

  Backend                 Python + FastAPI        REST API and business
                                                  logic

  Validation              Pydantic                Request/response and
                                                  agent-output schemas

  ORM/migrations          SQLAlchemy + Alembic    Database access and
                                                  schema evolution

  Database                PostgreSQL              Users, feedback,
                                                  evidence metadata,
                                                  reports, audit records

  Agent orchestration     LangGraph               Stateful workflow and
                                                  approval pauses

  LLM integration         Provider-neutral        Structured extraction
                          adapter                 and report drafting

  Semantic retrieval      Optional pgvector       Similarity search over
                                                  authorized evidence

  Testing                 pytest, Vitest,         Backend, frontend, and
                          Playwright              end-to-end tests

  Local services          Docker Compose, where   Repeatable local
                          practical               PostgreSQL and
                                                  supporting services

  Version control         Git + GitHub            History, collaboration,
                                                  and milestones
  -----------------------------------------------------------------------

### 9.2 Architecture overview

``` text
Browser
  |
  v
Next.js Frontend
  |
  | HTTPS/JSON API
  v
FastAPI Backend
  |-- Authentication and authorization
  |-- Users, teams, goals, feedback, review cycles
  |-- Evidence upload and retrieval
  |-- Report and approval service
  |-- Audit log service
  |
  v
LangGraph Workflow
  |-- Evidence Retrieval
  |-- Feedback Analysis
  |-- Bias & Evidence Audit
  |-- Report Synthesis
  |-- Output Validation
  |-- Human Approval Pause
  |
  +------> Approved/Configured LLM Provider
  |
  v
PostgreSQL
  |-- Business records
  |-- Workflow/report versions
  |-- Evidence metadata and source references
  |-- Audit logs
```

The frontend must never connect directly to PostgreSQL or expose
provider API keys. All data access passes through the backend
authorization layer.

### 9.3 Suggested repository structure

``` text
PERFORMai-360-Fresh/
├── apps/
│   └── web/                    # Next.js frontend
├── backend/
│   ├── app/
│   │   ├── api/                # API routers
│   │   ├── core/               # Settings, security, logging
│   │   ├── db/                 # Database and session management
│   │   ├── models/             # SQLAlchemy models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic
│   │   ├── agents/             # Agent nodes and workflow
│   │   ├── workflows/          # LangGraph orchestration
│   │   ├── repositories/       # Data access layer, if useful
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   ├── pyproject.toml
│   └── .env.example
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── API_CONTRACTS.md
│   ├── DATABASE_SCHEMA.md
│   ├── SECURITY_PRIVACY.md
│   ├── TEST_PLAN.md
│   └── PHASE_LOG.md
├── scripts/
│   └── seed_demo_data.py
├── docker-compose.yml
├── .gitignore
├── README.md
└── LICENSE (only if the team chooses one)
```

This is a target structure, not a requirement to create every file
immediately. Antigravity must create folders and files phase by phase
and avoid placeholder files that are not used.

## 10. Data Model (Initial Logical Design)

Use UUIDs or another consistent non-guessable identifier for primary
keys. Define foreign keys and indexes in migrations.

-   **User:** id, name, email, password_hash or identity-provider
    reference, role, active status, timestamps.
-   **Team:** id, name, manager reference, timestamps.
-   **TeamMembership:** user/team association and effective dates if
    needed.
-   **ReviewCycle:** id, employee_id, owner_id, period_start,
    period_end, status, template, timestamps.
-   **Feedback:** id, cycle_id, subject_employee_id, author_id,
    feedback_type, content, visibility, timestamps.
-   **Goal:** id, cycle_id, description, measurable_target, status,
    due_date, outcome_notes.
-   **Evidence:** id, cycle_id, source_type, title, storage_reference,
    source_date, uploader_id, metadata, access policy.
-   **Finding:** id, cycle_id, finding_type, statement, evidence
    references, origin type, limitations, validation status.
-   **BiasFlag:** id, cycle_id, flag_type, explanation, severity,
    evidence references, status, reviewer comment.
-   **WorkflowRun:** id, cycle_id, workflow status, stage state,
    provider/model metadata, timestamps, safe error metadata.
-   **ReviewReport:** id, cycle_id, version_number, structured content,
    status, generated_by_run_id, created_by, timestamps.
-   **Approval:** id, report_id, reviewer_id, decision, comments,
    timestamp.
-   **AuditEvent:** id, actor_id, action, resource_type, resource_id,
    timestamp, metadata.

Do not store arbitrary model output as trusted business data without
schema validation. Store validated structured report content and retain
relevant source references.

## 11. Initial API Contract

Use a versioned prefix such as `/api/v1`. Exact endpoint names may be
refined during the architecture phase, but contracts must be documented
before dependent frontend features are implemented.

  ---------------------------------------------------------------------------------------------
  Method                  Example endpoint                             Purpose
  ----------------------- -------------------------------------------- ------------------------
  POST                    `/api/v1/auth/login`                         Authenticate a user

  POST                    `/api/v1/auth/logout`                        End session where
                                                                       applicable

  GET                     `/api/v1/me`                                 Current user's profile
                                                                       and role

  GET/POST                `/api/v1/teams`                              List/create authorized
                                                                       teams

  GET/POST                `/api/v1/employees`                          List/create authorized
                                                                       employee records

  GET/POST                `/api/v1/review-cycles`                      List/create review
                                                                       cycles

  GET/PATCH               `/api/v1/review-cycles/{id}`                 Read/update permitted
                                                                       cycle

  POST                    `/api/v1/review-cycles/{id}/feedback`        Submit feedback

  GET/POST                `/api/v1/review-cycles/{id}/goals`           List/create goals

  POST                    `/api/v1/review-cycles/{id}/evidence`        Upload/register evidence

  POST                    `/api/v1/review-cycles/{id}/analysis-runs`   Start analysis workflow

  GET                     `/api/v1/workflow-runs/{id}`                 Inspect permitted
                                                                       workflow status

  GET                     `/api/v1/review-cycles/{id}/findings`        Retrieve validated
                                                                       findings

  GET                     `/api/v1/review-cycles/{id}/bias-flags`      Retrieve audit flags

  GET/POST                `/api/v1/review-cycles/{id}/reports`         List/create draft
                                                                       versions

  PATCH                   `/api/v1/reports/{id}`                       Edit an authorized draft

  POST                    `/api/v1/reports/{id}/approval`              Approve/reject/request
                                                                       changes

  GET                     `/api/v1/audit-events`                       Read audit events if
                                                                       authorized
  ---------------------------------------------------------------------------------------------

Requirements: - Document request/response examples and error formats. -
Validate IDs and ownership/authorization for every request. - Return
`401` for unauthenticated access and `403` for authenticated but
unauthorized access where appropriate. - Return `404` when resource
disclosure policy requires hiding its existence. - Use `409` for invalid
state transitions or conflicting updates when appropriate. - Add
pagination to list endpoints. - Never expose secrets or stack traces in
API responses.

## 12. AI Output Schemas and Guardrails

### 12.1 Finding schema (illustrative)

``` json
{
  "finding_type": "achievement",
  "statement": "Contributed to improving API error handling.",
  "origin_type": "evidence_supported",
  "evidence_ids": ["EV-102"],
  "limitations": [],
  "confidence": null
}
```

The example is illustrative. IDs must refer to real evidence records
retrieved for that review. The system must not accept fabricated
evidence IDs.

### 12.2 Bias flag schema (illustrative)

``` json
{
  "flag_type": "recency_concentration",
  "explanation": "The draft emphasizes events from the final week while earlier review-period evidence is available.",
  "severity": "review",
  "evidence_ids": ["EV-102", "EV-118"],
  "suggested_action": "Check whether earlier contributions have been considered.",
  "status": "open"
}
```

### 12.3 Report generation rules

-   Use only authorized evidence and validated findings.
-   Cite source IDs next to factual claims or provide a traceable
    evidence panel.
-   Never invent metrics or turn opinions into verified facts.
-   Keep negative and positive evidence subject to the same grounding
    standard.
-   Avoid protected-trait inference and personality diagnosis.
-   Clearly state when evidence is incomplete, conflicting, or
    self-reported.
-   The final report must preserve human edits and approval history.
-   Treat model-generated confidence as uncalibrated unless calibration
    has been empirically evaluated.

## 13. Evaluation Plan

Evaluation is required before the project can claim success. The team
must record actual test results and not invent performance numbers.

### 13.1 Evidence grounding

-   Prepare a test set of report claims with known supporting evidence.
-   Measure the percentage of factual claims with valid source IDs.
-   Manually inspect whether cited evidence actually supports the
    associated claim.
-   Report unsupported-claim rate and citation validity separately.

### 13.2 Bias-audit performance

-   Create synthetic scenarios with documented labels for the audit
    categories.
-   Have at least two reviewers independently label a subset when
    practical, resolve disagreements, and document the rubric.
-   Measure precision, recall, and F1 for each flag type where the
    labels support those metrics.
-   Report false positives and false negatives; do not treat every flag
    as proof of bias.

### 13.3 Workflow reliability

-   Verify that stages run in the expected order.
-   Test malformed model output, timeout, provider failure, and missing
    evidence.
-   Verify bounded retries and safe recovery.
-   Verify that a report cannot be finalized without required human
    approval.

### 13.4 Usability

-   Ask representative test users to complete a review workflow using
    synthetic data.
-   Use a documented rubric for clarity, source traceability, editing
    effort, and actionability.
-   Record findings and changes made after testing.

### 13.5 Security and governance

-   Test role boundaries and cross-employee access attempts.
-   Test file upload validation.
-   Verify that secrets are absent from Git history and logs.
-   Verify audit records for report edits and approval decisions.
-   Test deletion/retention behavior as implemented.

## 14. Acceptance Criteria for the Complete MVP

The MVP is considered ready for demonstration only when all the
following are true:

1.  A developer can set up the application from documented instructions
    on macOS.
2.  The frontend and backend start locally without undocumented manual
    steps.
3.  Database migrations create the required schema from a clean
    database.
4.  Seed data uses synthetic employees and feedback.
5.  Each role can perform permitted actions and is denied unauthorized
    actions.
6.  A manager can create a review cycle and collect self, peer, and
    manager feedback.
7.  A user can attach evidence to a review cycle.
8.  The workflow retrieves only authorized evidence for the selected
    review.
9.  The analysis produces validated structured findings with real source
    references.
10. The audit stage detects the supported MVP evidence-quality patterns
    on the test set.
11. The report includes strengths, growth areas, goals, impact, flags,
    and limitations.
12. The UI lets an authorized manager inspect sources, edit the draft,
    and approve/reject/request changes.
13. An unapproved report cannot be finalized through the API or UI.
14. Important actions and report versions are auditable.
15. Backend, frontend, and critical end-to-end tests pass.
16. Setup, architecture, API, test, privacy, and phase-log documentation
    is complete.
17. The demo can be completed end-to-end without using real employee
    data.
18. Known limitations are documented honestly.

## 15. Phase-Wise Implementation Plan for Antigravity

**Execution rule:** Complete one phase at a time. Do not implement all
phases in a single prompt. At the end of each phase, run the relevant
checks, summarize modified files, report test results, list known
issues, and wait for the student to approve continuation.

### Phase 0 --- Repository and planning baseline

Deliverables: - Review this PRD and confirm assumptions. - Create
`README.md`, `docs/PRD.md`, `docs/PHASE_LOG.md`, and a short
`docs/ARCHITECTURE.md`. - Add/verify `.gitignore` for Python, Node.js,
macOS, virtual environments, build artifacts, local databases, uploads,
and secrets. - Add `.env.example` with placeholder values only. -
Document the chosen runtime versions and local commands. - Do not build
application features yet.

Acceptance: - No secrets or real personal data committed. -
Documentation matches the agreed stack. - `git status` is understood and
clean after the baseline commit.

### Phase 1 --- Application skeleton and local developer environment

Deliverables: - Create the Next.js TypeScript frontend in `apps/web`. -
Create the FastAPI backend in `backend`. - Add health endpoint and
frontend/backend environment configuration. - Add basic linting,
formatting, and test commands. - Add Docker Compose for PostgreSQL if it
improves repeatability. - Add a clear root-level setup guide.

Acceptance: - Frontend opens locally. - Backend health endpoint returns
a successful response. - Database service can start locally. - No
secrets are required for the initial skeleton. - Basic automated checks
pass.

### Phase 2 --- Database, migrations, and authentication

Deliverables: - SQLAlchemy models and Alembic migrations. - User, team,
membership, and review-cycle foundations. - Authentication and
server-side role checks. - Safe synthetic seed data and documented demo
setup.

Acceptance: - Clean migration works. - Login/logout and `/me` work. -
Role/ownership tests pass. - Unauthorized requests are rejected.

### Phase 3 --- Core review workflow

Deliverables: - Employee/team views. - Review-cycle create/read/update
and state transitions. - Feedback forms for self, peer, and manager
feedback. - Goal management. - Evidence upload/reference management. -
Audit events for key actions.

Acceptance: - End-to-end manual review data entry works. - Validation
and permission tests pass. - Upload restrictions work. - Records are
isolated by authorized scope.

### Phase 4 --- Evidence processing and retrieval

Deliverables: - Safe parsers for the selected file formats. - Evidence
metadata and source references. - Review-period and permission-aware
retrieval. - Evidence completeness indicators. - Tests proving one
employee's evidence cannot leak into another review.

Acceptance: - Source records can be opened from the UI. -
Invalid/oversized files are rejected. - Missing evidence is reported
explicitly. - Retrieval tests pass.

### Phase 5 --- Single-pass AI analysis and grounded report draft

Deliverables: - Provider-neutral LLM adapter. - Typed structured
outputs. - Feedback analysis and draft report generation. - Evidence IDs
validated against actual retrieved records. - Clear failure handling for
missing keys, provider errors, and malformed output.

Acceptance: - A synthetic review can produce a draft. - Unsupported
claims are omitted or marked uncertain. - Every factual finding has a
traceable source or an explicit limitation. - The app remains usable if
the LLM provider is unavailable.

### Phase 6 --- Bias/evidence audit

Deliverables: - Deterministic rules for evidence coverage, recency
concentration, stakeholder coverage, vague claims, and possible
contradictions. - Structured flags with explanation, source references,
status, and suggested reviewer action. - Flag review interface. -
Synthetic labeled test set and evaluation report.

Acceptance: - All audit rules have unit tests. - Results are
explainable. - Flags do not make definitive claims about intent or
discrimination. - Precision/recall/F1 are reported only when supported
by labeled test data.

### Phase 7 --- LangGraph multi-agent orchestration

Deliverables: - Evidence retrieval, analysis, audit, and synthesis
nodes. - Typed stage contracts and workflow state. - Bounded retries,
timeouts, failure states, and run status. - Approval pause and safe
resume behavior. - Workflow visualization/status in the UI where useful.

Acceptance: - Stages run in the intended order. - Invalid stage output
cannot silently progress. - Workflow failures are inspectable. - The
workflow can pause for approval and resume safely. - No agent can bypass
access control or human approval.

### Phase 8 --- Human approval, report versions, and governance

Deliverables: - Editable draft report. - Approve, reject, and
request-changes actions. - Version history and approval records. - Audit
log UI for authorized roles. - Finalization guards and safe
re-generation behavior.

Acceptance: - Unapproved reports cannot be finalized. - Human edits are
not silently overwritten. - Approval is tied to an exact report
version. - Audit records show actor, action, resource, and timestamp.

### Phase 9 --- Dashboard polish, export, and accessibility

Deliverables: - Dashboard summaries, empty/error/loading states,
filters, and responsive layouts. - Accessibility improvements. -
PDF/DOCX export if core functionality is stable. - UI consistency and
usability review.

Acceptance: - Critical workflows are usable by keyboard. - Status is not
conveyed by color alone. - Exported reports preserve source references
and limitations. - No P0 feature regresses.

### Phase 10 --- Comprehensive testing and security review

Deliverables: - Backend unit/integration tests. - Frontend component
tests. - Critical Playwright end-to-end tests. - Authorization and
upload-security tests. - Dependency/configuration review. - Performance
baseline and known-limitations list.

Acceptance: - All critical tests pass. - Known failures are documented
and prioritized. - Secrets and real employee data are absent from the
repository. - Human approval and data-isolation controls are verified.

### Phase 11 --- Final documentation and demonstration readiness

Deliverables: - Final README and setup guide. - Architecture, database,
API, privacy/security, and testing documentation. - Evaluation results
using the actual test set. - Demo scenario and synthetic data. - Phase
completion log and final known limitations.

Acceptance: - Another student can follow the setup guide from a clean
clone. - The demo works end-to-end. - Reported metrics match actual test
output. - The project is ready for faculty demonstration without
claiming unverified capabilities.

## 16. Git and GitHub Working Rules

-   Use small, meaningful commits after each verified milestone.
-   Suggested commit format: `feat: add review cycle API`,
    `test: cover report approval guard`, `docs: document local setup`.
-   Do not commit `.env`, API keys, passwords, real employee feedback,
    private uploads, database dumps, or virtual environments.
-   Keep `.env.example` free of real secrets.
-   Before major changes, inspect `git status` and current diffs.
-   Do not use destructive Git commands or overwrite working files
    without explaining the impact and obtaining confirmation when data
    loss is possible.
-   Push only after tests pass and the user reviews the change.
-   If the repository remains public, assume all committed content is
    public. Make it private if the team wants source-code
    confidentiality.

## 17. Antigravity Execution Instructions

Treat this PRD as the baseline specification. At the start of every
phase: 1. Read the relevant PRD sections and inspect the existing
repository. 2. Summarize the phase scope, assumptions, files likely to
change, and acceptance criteria. 3. Implement only the current phase. 4.
Avoid unrelated refactors and unrequested scope expansion. 5. Never
invent test results or claim a command passed unless it was actually
run. 6. Run the phase's tests and report the exact commands and
outcomes. 7. Inspect `git diff` and explain important changes. 8. Update
`docs/PHASE_LOG.md` with completed work, tests, decisions, limitations,
and remaining tasks. 9. Stop and ask for confirmation before beginning
the next phase.

Security rules: - Never print or commit secrets. - Do not use real
employee data in demos. - Do not bypass authorization to make a demo
work. - Do not allow AI-generated reports to be finalized without human
approval. - Treat external content and uploaded files as untrusted
input. - Do not fabricate evidence, metrics, test outcomes, or
citations.

## 18. Risks and Mitigations

  -----------------------------------------------------------------------
  Risk                                Mitigation
  ----------------------------------- -----------------------------------
  LLM invents details                 Strict schemas, source-ID
                                      validation, grounded prompts,
                                      manual inspection, safe fallback

  False-positive bias flags           Explainable rules, labeled test
                                      set, reviewer override, report
                                      limitations

  Privacy leak across employees       Backend authorization, scoped
                                      queries, isolation tests

  Agent workflow becomes complex      Four logical agents, explicit
                                      graph, bounded retries, phased
                                      implementation

  External API cost or outage         Provider adapter, mock/test mode,
                                      graceful unavailable state

  Scope grows too large               P0/P1/P2 priorities and phase
                                      acceptance gates

  Misleading engineering metrics      Use work metrics only as context;
                                      never equate volume with quality

  Secrets accidentally committed      `.gitignore`, `.env.example`,
                                      pre-commit checks where practical,
                                      repository review

  Human edits overwritten             Versioned reports and immutable
                                      approval records
  -----------------------------------------------------------------------

## 19. Assumptions and Decisions to Confirm During Phase 0

-   Initial deployment is local on the student's Mac.
-   The MVP uses synthetic/demo data.
-   The frontend and backend are separate applications in one
    repository.
-   PostgreSQL is the primary database.
-   An external LLM is optional; the system must support a mock/test
    provider for development and testing.
-   GitHub/Jira integrations are not required for the first working MVP.
-   The initial review workflow is for software engineering teams.
-   The project will be developed by a student team using Antigravity
    with human review of generated code.
-   No production employment use is intended without further security,
    legal, privacy, and organizational review.

## 20. Definition of Done

A phase is done only when: - Its stated deliverables exist and are
integrated. - Acceptance criteria have been checked. - Tests were
actually run and results recorded. - No known blocker is hidden. -
Documentation and `docs/PHASE_LOG.md` are updated. - Changes have been
inspected with Git. - The user has reviewed the result and explicitly
approved moving forward.

**Final product principle:** PERFORMai-360 should help people make
better-informed performance reviews by organizing evidence and
highlighting uncertainty. It must remain transparent, privacy-conscious,
auditable, and under meaningful human control.
