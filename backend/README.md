# PERFORMai-360 Backend (FastAPI)

FastAPI application providing REST endpoints, evaluation workflow orchestration, domain services, repositories, and database persistence for **PERFORMai-360**.

---

## 1. Directory Structure

```text
backend/
├── app/
│   ├── ai/                           # AI orchestration, context builder, providers, and citation validators
│   │   ├── base.py                   # LLMProvider abstract interface & exceptions
│   │   ├── context_builder.py        # Authorized bounded evidence context builder
│   │   ├── orchestrator.py           # AIOrchestrator pipeline coordinator
│   │   ├── prompts.py                # System instructions, prompt injection defenses, JSON schemas
│   │   ├── provider.py               # Mock, OpenAI, Anthropic, Ollama & Disabled providers
│   │   └── validators.py             # Citation validation, hallucination filter, statement sanitization
│   ├── audit/                        # Phase 6 Deterministic bias & evidence-quality audit engine
│   │   ├── base.py                   # AuditRule abstract base class, AuditContext, AuditFlagDraft
│   │   ├── engine.py                 # AuditEngine orchestrator, health scoring, review-ready checks
│   │   └── rules/                    # 5 deterministic rule implementations
│   │       ├── evidence_coverage.py  # EvidenceCoverageRule (uncited material claims)
│   │       ├── recency_concentration.py # RecencyConcentrationRule (>60% in final quartile)
│   │       ├── stakeholder_coverage.py # StakeholderCoverageRule (missing self/peer/mgr)
│   │       ├── vague_language.py     # VagueLanguageRule (absolutes & personality adjectives)
│   │       └── contradictions.py     # ContradictoryFeedbackRule (unresolved conflicting sentiment)
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── health.py         # Liveness and readiness probes
│   │       │   ├── users.py          # User management endpoints
│   │       │   ├── teams.py          # Team & membership endpoints
│   │       │   ├── review_cycles.py  # Review cycle workflow & nested endpoints
│   │       │   ├── feedback.py       # 360-degree feedback management
│   │       │   ├── goals.py          # Goal tracking & progress management
│   │       │   ├── evidence.py       # Evidence upload, retrieval & access policy management
│   │       │   ├── review_analysis.py # Evidence-grounded AI review analysis endpoints
│   │       │   ├── bias_audit.py     # Deterministic bias & quality audit endpoints
│   │       │   ├── reports.py        # Report governance, versioning, approvals & PDF/DOCX exports
│   │       │   └── analytics.py      # Real-time aggregated PostgreSQL analytics
│   │       └── router.py             # API v1 router aggregator
│   ├── core/
│   │   ├── config.py                 # Pydantic Settings configuration (LLM, upload limits, storage dir)
│   │   └── security.py               # Security principal resolution, role normalization & RBAC guards
│   ├── db/
│   │   ├── base.py                   # SQLAlchemy 2.0 Base, naming conventions & mixins
│   │   └── session.py                # Async SQLAlchemy engine, session generator & health probe
│   ├── models/                       # SQLAlchemy 2.0 ORM domain entities (all PRD models)
│   ├── parsers/                      # Safe document parsers (PDF, DOCX, TXT, CSV) & magic signature validation
│   ├── schemas/                      # Pydantic v2 validation & serialization schemas
│   ├── repositories/                 # Repository layer (DB queries, mutations, analytics, versions, reports)
│   ├── services/                     # Business logic, analytics, report export (PDF/DOCX), governance services
│   ├── workflows/                    # Phase 7 LangGraph multi-agent orchestration
│   │   ├── state.py                  # MultiAgentWorkflowState TypedDict
│   │   ├── nodes.py                  # 4 specialist agents, HumanApprovalPauseNode, FinalizationNode, RevisionHandlerNode
│   │   └── graph.py                  # StateGraph compiler, edges, and conditional routing
│   └── main.py                       # FastAPI application entry point, CORS & lifespan
├── migrations/                       # Alembic async migration scripts & env.py
├── tests/                            # Pytest test suite (144 automated tests, 100% pass)
├── alembic.ini                       # Alembic database migration configuration
└── pyproject.toml                    # Dependency specifications & tool configs
```

---

## 2. Local Setup and Execution

### Create & Activate Virtual Environment
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

### Run Database Migrations
```bash
alembic upgrade head
```

### Run the Development Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Run Automated Tests
```bash
pytest tests -v
```

### Run Linter & Formatter
```bash
ruff check .
ruff format . --check
```

---

## 3. Available API Endpoints

### Health & Readiness Probes
| Method | Endpoint | Description | Expected Status |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Liveness check (process up) | `200 OK` |
| `GET` | `/health/ready` | Readiness check (PostgreSQL reachable, LLM provider ready) | `200 OK` (healthy) or `503` |
| `GET` | `/api/v1/health` | Mounted v1 liveness check | `200 OK` |
| `GET` | `/api/v1/health/ready` | Mounted v1 readiness check | `200 OK` or `503` |
| `GET` | `/docs` | Interactive Swagger API docs | `200 OK` |

### Human Approval, Report Versioning & Governance (Phase 8)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/reports/{report_id}` | Retrieve report details, active status, current version number, and structured content |
| `GET` | `/api/v1/review-cycles/{cycle_id}/report` | Retrieve active or finalized report for a specific review cycle |
| `POST` | `/api/v1/reports/{report_id}/sections/{section_key}` | Edit an individual section with optimistic concurrency control (`base_version_number`) |
| `GET` | `/api/v1/reports/{report_id}/versions` | List all historical immutable versions and author metadata for a report |
| `GET` | `/api/v1/reports/{report_id}/versions/{version_id_or_number}` | Retrieve exact immutable structured content snapshot for a specific version |
| `GET` | `/api/v1/reports/{report_id}/compare` | Deterministic version comparison (unified text diffs & structured list deltas) |
| `POST` | `/api/v1/reports/{report_id}/approve` | Authorized human sign-off bound to exact version number/ID; rejects stale approvals |
| `POST` | `/api/v1/reports/{report_id}/request-revision` | Transition report to `revision_requested` with mandatory reviewer instructions |
| `GET` | `/api/v1/reports/{report_id}/approvals` | List approval and revision decision records associated with a report |
| `GET` | `/api/v1/reports/{report_id}/audit-events` | Retrieve traceable governance audit event trail (`report.section_edited`, `report.approved`, etc.) |

### LangGraph Multi-Agent Orchestration & Human-in-the-Loop Review (Phase 7)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/review-cycles/{cycle_id}/workflows` | Initiate or retrieve multi-agent orchestration workflow (runs 4 agents, pauses at approval boundary) |
| `POST` | `/api/v1/review-cycles/{cycle_id}/workflow-runs` | Alias endpoint returning `201 Created` with full status and stage breakdown |
| `GET` | `/api/v1/review-cycles/{cycle_id}/workflows` | List all historical and active workflow runs for the review cycle |
| `GET` | `/api/v1/workflows/{workflow_id}` | Retrieve comprehensive status, current stage, 5-stage progress, synthesized draft, and available actions |
| `POST` | `/api/v1/workflows/{workflow_id}/approve` | Authorized manager sign-off: approves review draft, marks status completed, logs immutable audit event |
| `POST` | `/api/v1/workflows/{workflow_id}/request-revision` | Request revisions with reviewer instructions: marks status revision_requested, logs audit event |
| `POST` | `/api/v1/workflows/{workflow_id}/resume` | Resume paused or interrupted workflow run from persisted PostgreSQL state |
| `POST` | `/api/v1/workflows/{workflow_id}/cancel` | Cancel an active, pending, or awaiting_approval workflow run |

### Deterministic Bias & Evidence-Quality Audit Engine (Phase 6)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/review-cycles/{cycle_id}/audit` | Run 5 deterministic audit rules against evidence, feedback, goals, and findings |
| `POST` | `/api/v1/review-cycles/{cycle_id}/bias-audit` | Alias endpoint returning `201 Created` with audit summary and generated flags |
| `GET` | `/api/v1/review-cycles/{cycle_id}/audit-flags` | List detected bias & evidence-quality flags (supports filtering by `status`, `severity`, `flag_type`) |
| `GET` | `/api/v1/review-cycles/{cycle_id}/bias-flags` | Alias endpoint listing bias flags |
| `PATCH` | `/api/v1/review-cycles/{cycle_id}/audit-flags/{flag_id}` | Manager triage & calibration (`open` → `acknowledged`, `resolved`, `not_applicable` with comment) |
| `GET` | `/api/v1/review-cycles/{cycle_id}/audit-summary` | Retrieve overall audit health score (0-100), severity breakdown, and review readiness |

### Review Analysis & Grounded Performance Insights (Phase 5)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/review-cycles/{cycle_id}/analysis` | Execute evidence-grounded review analysis, persist findings & draft report |
| `POST` | `/api/v1/review-cycles/{cycle_id}/analysis-runs` | Alias endpoint returning `201 Created` |
| `GET` | `/api/v1/review-cycles/{cycle_id}/analysis/{analysis_id}` | Retrieve specific analysis by ID with cross-cycle isolation checks |
| `GET` | `/api/v1/review-cycles/{cycle_id}/analysis` | Retrieve latest analysis for the review cycle |
| `GET` | `/api/v1/review-cycles/{cycle_id}/findings` | Retrieve atomic findings (strengths, improvement opportunities, contradictions) |

### Review Cycle Workflow (Phase 3)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/review-cycles` | List review cycles (filtering: `employee_id`, `status`; pagination: `skip`, `limit`) |
| `POST` | `/api/v1/review-cycles` | Create a review cycle (`draft` status by default, date range validation) |
| `GET` | `/api/v1/review-cycles/{cycle_id}` | Retrieve review cycle by ID |
| `PATCH` | `/api/v1/review-cycles/{cycle_id}` | Update review cycle fields & lifecycle transitions (`draft` → `active` → `in_review` → `completed` → `archived`) |
| `DELETE` | `/api/v1/review-cycles/{cycle_id}` | Delete a review cycle (permitted only in `draft` status) |

### 360-Degree Feedback Management (Phase 3)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/feedback` | List feedback (filtering: `cycle_id`, `employee_id`, `author_id`, `feedback_type`, visibility checks) |
| `POST` | `/api/v1/feedback` | Submit feedback (body must include `cycle_id`; requires active cycle; validates author/subject relationship) |
| `GET` | `/api/v1/feedback/{id}` | Retrieve feedback by ID (enforces visibility permissions; hides unauthorized records with 404) |
| `PATCH` | `/api/v1/feedback/{id}` | Update feedback content, category, or visibility |
| `DELETE` | `/api/v1/feedback/{id}` | Delete feedback record |
| `GET` | `/api/v1/review-cycles/{cycle_id}/feedback` | List feedback nested under a specific review cycle |
| `POST` | `/api/v1/review-cycles/{cycle_id}/feedback` | Submit feedback directly to a review cycle |

### Goal Progress Tracking (Phase 3)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/goals` | List goals (filtering: `cycle_id`, `employee_id`, `status`) |
| `POST` | `/api/v1/goals` | Create a goal (body must include `cycle_id`) |
| `GET` | `/api/v1/goals/{id}` | Retrieve goal by ID |
| `PATCH` | `/api/v1/goals/{id}` | Update goal fields (`description`, `measurable_target`, `status`, `outcome_notes`, `due_date`) |
| `DELETE` | `/api/v1/goals/{id}` | Delete goal record |
| `GET` | `/api/v1/review-cycles/{cycle_id}/goals` | List goals nested under a review cycle |
| `POST` | `/api/v1/review-cycles/{cycle_id}/goals` | Create goal directly under a review cycle |

### Evidence Management & Processing (Phase 3 & Phase 4)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/evidence` | List evidence (filtering: `cycle_id`, `employee_id`, `source_type`, `start_date`, `end_date`, access policies) |
| `POST` | `/api/v1/evidence` | Register evidence metadata (source types: `pr`, `commit`, `design_doc`, `ticket`, `document_upload`) |
| `POST` | `/api/v1/evidence/upload` | Multipart file upload (PDF, DOCX, TXT, CSV), magic signature validation, safe text parsing |
| `GET` | `/api/v1/evidence/{id}` | Retrieve evidence by ID (enforces access policy: `internal`, `manager_only`, `restricted`, `confidential`) |
| `GET` | `/api/v1/evidence/{id}/content` | Download or view stored document file (enforces cycle, employee, and role permissions) |
| `PATCH` | `/api/v1/evidence/{id}` | Update evidence title, source type, metadata, or access policy |
| `DELETE` | `/api/v1/evidence/{id}` | Delete evidence record and unlink physical storage |
| `GET` | `/api/v1/review-cycles/{cycle_id}/evidence` | List evidence nested under a review cycle |
| `POST` | `/api/v1/review-cycles/{cycle_id}/evidence` | Register evidence directly under a review cycle |
| `POST` | `/api/v1/review-cycles/{cycle_id}/evidence/upload` | Upload and parse document directly into a review cycle |
| `GET` | `/api/v1/review-cycles/{cycle_id}/evidence/completeness` | Cycle evidence completeness score, source distribution, and explicit gap detection |

### Report Governance, Versioning & Exports (Phase 8 & Phase 9)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/review-cycles/{cycle_id}/report` | Retrieve active report for cycle with version and approval metadata |
| `PATCH` | `/api/v1/reports/{report_id}/sections/{section_key}` | Edit section with optimistic concurrency (`base_version_number`) |
| `GET` | `/api/v1/reports/{report_id}/versions` | List historical immutable report versions |
| `GET` | `/api/v1/reports/{report_id}/versions/{version_number}` | Retrieve exact structured snapshot for historical version |
| `GET` | `/api/v1/reports/{report_id}/compare` | Deterministic diff comparison between two versions |
| `POST` | `/api/v1/reports/{report_id}/approve` | Version-bound human manager approval |
| `POST` | `/api/v1/reports/{report_id}/request-revision` | Request revisions on active report draft |
| `GET` | `/api/v1/reports/{report_id}/audit-events` | Fetch immutable governance audit events |
| `GET` | `/api/v1/reports/{report_id}/export/pdf` | Export branded PDF report with dynamic page count & sign-off callouts |
| `GET` | `/api/v1/reports/{report_id}/export/docx` | Export professional Word `.docx` report with styled tables & decision banner |

### Performance & Governance Analytics (Phase 9)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/analytics/overview` | Review totals, mathematical completion rate, health score, governance metrics |
| `GET` | `/api/v1/analytics/reviews` | Review cycle list and lifecycle status distribution |
| `GET` | `/api/v1/analytics/evidence` | Evidence source & policy breakdown, cited vs ungrounded claims |
| `GET` | `/api/v1/analytics/audits` | Deterministic bias flags by rule, severity, and health score distribution |
| `GET` | `/api/v1/analytics/trends` | Time-bucketed trends (`day`, `week`, `month`) for cycles, evidence & approvals |

### Foundational Entities (Phase 2)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/users` | List users (filtering: `role`) |
| `POST` | `/api/v1/users` | Create user (unique email) |
| `GET` | `/api/v1/users/{id}` | Retrieve user by ID |
| `GET` | `/api/v1/teams` | List teams |
| `POST` | `/api/v1/teams` | Create team (unique name) |
| `GET` | `/api/v1/teams/{id}` | Retrieve team by ID |
| `POST` | `/api/v1/teams/{id}/members` | Add member to team |
| `GET` | `/api/v1/teams/{id}/members` | List team memberships |

---

## 4. LLM Provider Configuration

The backend supports multiple LLM providers configured via environment variables:

- `LLM_PROVIDER="mock"`: Deterministic in-memory provider. Synthesizes findings strictly from authorized evidence items. Zero API costs, runs in <10ms, perfect for local development and CI testing.
- `LLM_PROVIDER="openai"`: Uses `OPENAI_API_KEY` with configured `OPENAI_MODEL` (default: `gpt-4o-mini`).
- `LLM_PROVIDER="anthropic"`: Uses `ANTHROPIC_API_KEY` with configured `ANTHROPIC_MODEL` (default: `claude-3-5-sonnet-20241022`).
- `LLM_PROVIDER="ollama"`: Local offline inference via `OLLAMA_BASE_URL` (default: `http://localhost:11434`) and `OLLAMA_MODEL`.
- `LLM_PROVIDER="none"`: Disabled mode. Reports AI analysis unavailable safely with HTTP 503 or structured failed response without crashing.
