# PERFORMai-360: AI-Driven Bias-Aware 360° Performance Evaluation for Software Engineering Teams

> **An evidence-grounded, human-in-the-loop performance review intelligence system designed to support software engineering teams with balanced, explainable, and reviewable evaluations.**

---

## 1. Executive Summary

**PERFORMai-360** assists engineering leaders, managers, and teams in synthesizing multi-source feedback into balanced, objective performance reviews. The system ingests employee self-assessments, peer feedback, manager assessments, goal achievements, and authorized project evidence. It analyzes contributions, audits reviews for potential bias and evidence gaps, and drafts structured reports for human review.

### Core Principles
- **Decision-Support Only:** PERFORMai-360 is strictly an assistive tool. It never independently determines compensation, promotions, hiring, or terminations.
- **Traceable Grounding:** AI findings must cite verifiable source evidence identifiers (`evidence_ids`). Hallucinations are actively prevented; missing evidence is flagged explicitly.
- **Explainable Bias & Quality Auditing:** Imbalances—such as recency concentration, missing stakeholder perspectives, or ungrounded claims—are flagged with plain-language explanations to assist human evaluators.
- **Mandatory Human Approval:** Reports cannot be finalized autonomously. Authorized human managers must inspect evidence, review flags, edit drafts, and explicitly approve the evaluation.
- **Privacy and Data Isolation:** Strict server-side role-based access control (RBAC) ensures employees, peers, and managers only access authorized data. Demos and tests strictly use synthetic data.

---

## 2. System Architecture & Tech Stack

```text
  [ Browser / Client ]
           │
           ▼
  [ Next.js App Router (TypeScript, Tailwind CSS, shadcn/ui) ]
           │  HTTPS / REST API
           ▼
  [ FastAPI Backend (Python 3.14+, Pydantic v2) ]
     ├── Auth & Role-Based Access Control
     ├── Core Services (Feedback, Goals, Evidence, Reports, Audit)
     └── LangGraph Multi-Agent Orchestrator
           ├── Evidence Retrieval Agent
           ├── Feedback Analysis Agent
           ├── Bias & Evidence Auditor
           └── Review Synthesis Agent
           │
           ├──▶ LLM Provider Adapter (Mock / OpenAI / Anthropic / Ollama)
           │
           ▼
  [ PostgreSQL Database (SQLAlchemy 2.0 Async + Alembic Migrations) ]
```

- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, Recharts, Lucide/Heroicons
- **Backend:** Python 3.14+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (asyncpg), Greenlet, ReportLab, python-docx
- **Database:** PostgreSQL 16 (Docker Compose with persistent volume `pgdata`, port 5433)
- **Agent Orchestration:** LangGraph state machine with deterministic approval pauses
- **AI Integration:** Provider-neutral adapter with offline mock support (no paid API key required)
- **Testing & Quality:** pytest + pytest-asyncio + httpx (backend, 132 tests, 100% pass), ESLint (frontend), Ruff (backend)

---

## 3. Verified Local Development Environment

| Requirement | Supported Version (Tested) | Notes |
| :--- | :--- | :--- |
| **Operating System** | macOS 14+ | Tested on Darwin arm64 |
| **Python** | 3.14.7 | Virtual environments via standard library `venv` |
| **Node.js** | v26.9.0 | Frontend runtime |
| **npm** | 12.2.0 | Frontend package manager |
| **Docker Compose** | v5.5.1 | Manages local PostgreSQL 16 container |
| **Git** | 2.55.0+ | Version control |

---

## 4. Repository Layout

```text
PERFORMai-360-Fresh/
├── apps/
│   └── web/                    # Next.js 16 frontend application
│       ├── app/                # App Router (layout.tsx, page.tsx, globals.css)
│       ├── components/         # Header, BackendHealthCard, PillarCards, Roadmap, Footer
│       ├── package.json        # Frontend dependencies & scripts
│       └── tsconfig.json
├── backend/
│   ├── app/                    # FastAPI backend package
│   │   ├── api/v1/             # API v1 routers (health, users, teams, review_cycles)
│   │   ├── core/               # Pydantic Settings configuration (config.py)
│   │   ├── db/                 # Base declarative model, mixins, async engine & session
│   │   ├── models/             # SQLAlchemy 2.0 ORM domain entities (all 13 PRD models)
│   │   ├── schemas/            # Pydantic v2 validation schemas
│   │   ├── repositories/       # Clean database access layer
│   │   ├── services/           # Business logic & domain validation services
│   │   └── main.py             # FastAPI entry point, CORS & lifespan
│   ├── migrations/             # Alembic database migration scripts & env.py
│   ├── tests/                  # Pytest automated test suite (models, APIs, health)
│   ├── alembic.ini             # Alembic migration configuration
│   ├── pyproject.toml          # Backend dependencies & tool configs (pytest, ruff)
│   └── README.md
├── docs/
│   ├── PRD.md                  # Comprehensive Product Requirements Document
│   ├── ARCHITECTURE.md         # Detailed System Architecture Specification
│   └── PHASE_LOG.md            # Chronological execution log & audit trail
├── docker-compose.yml          # PostgreSQL 16 local service configuration
├── .env.example                # Configuration template with placeholders only
├── .gitignore                  # Git ignore rules for macOS, Python, Node, secrets
└── README.md                   # Project overview and instructions
```

---

## 5. Phased Implementation Roadmap

Development proceeds strictly in sequential phases:

- [x] **Phase 0 — Repository and Planning Baseline** *(Completed)*
- [x] **Phase 1 — Application Foundation & Local Developer Environment** *(Completed)*
- [x] **Phase 2 — Core Database Models and Persistence** *(Completed)*
- [x] **Phase 3 — Core Review Workflow** *(Completed)*
- [x] **Phase 4 — Evidence Processing & Retrieval** *(Completed)*
- [x] **Phase 5 — Single-Pass AI Analysis & Grounded Report Draft** *(Completed)*
- [x] **Phase 6 — Bias & Evidence-Quality Audit Engine** *(Completed)*
- [x] **Phase 7 — LangGraph Multi-Agent Orchestration** *(Completed)*
- [x] **Phase 8 — Human Approval, Report Versions, & Governance** *(Completed)*
- [ ] **Phase 9 — Dashboard Polish, Accessibility, & Export**
- [ ] **Phase 10 — Comprehensive Testing & Security Review**
- [ ] **Phase 11 — Final Documentation & Demonstration Readiness**

Refer to [docs/PHASE_LOG.md](file:///Users/kaustubhkadam/Desktop/PERFORMai-360-Fresh/docs/PHASE_LOG.md) for detailed milestone records.

---

## 6. Developer Quick Start

### 1. Database (PostgreSQL via Docker Compose)
```bash
# Start PostgreSQL container in background
docker compose up -d

# Check container status and health
docker compose ps

# View logs
docker compose logs -f postgres

# Stop database
docker compose down
```

### 2. Backend (FastAPI)
```bash
# Enter backend directory and create virtual environment
cd backend
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install editable package with dev dependencies
pip install --upgrade pip
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Run automated tests (95 tests)
pytest tests -v

# Run code linter and format check
ruff check .
ruff format . --check

# Start development server (runs on http://localhost:8000)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend (Next.js 16)
```bash
# Enter web application directory
cd apps/web

# Install dependencies (if not already installed)
npm install

# Run code linter
npm run lint

# Build production bundle
npm run build

# Start development server (runs on http://localhost:3000)
npm run dev
```

---

## 7. Available API Endpoints

### Health & Readiness Probes
| Method | Endpoint | Description | Return Status |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Liveness check (process alive) | `200 OK` |
| `GET` | `/health/ready` | Readiness check (PostgreSQL reachable) | `200 OK` (connected) or `503` (down) |
| `GET` | `/api/v1/health` | Mounted v1 liveness probe | `200 OK` |
| `GET` | `/api/v1/health/ready`| Mounted v1 readiness probe | `200 OK` or `503` |
| `GET` | `/docs` | Interactive Swagger API documentation | `200 OK` |

### LangGraph Multi-Agent Orchestration & Human-in-the-Loop Review (Phase 7)
| Method | Endpoint | Description | Return Status |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/review-cycles/{id}/workflows` | Initiate or retrieve multi-agent orchestration workflow (runs 4 agents, pauses at approval boundary) | `200 OK` |
| `POST` | `/api/v1/review-cycles/{id}/workflow-runs` | Alias endpoint returning 201 Created with full status and stage breakdown | `201 Created` |
| `GET` | `/api/v1/review-cycles/{id}/workflows` | List all historical and active workflow runs for the review cycle | `200 OK` |
| `GET` | `/api/v1/workflows/{id}` | Retrieve comprehensive status, current stage, 5-stage progress, synthesized draft, and available actions | `200 OK` or `404 Not Found` |
| `POST` | `/api/v1/workflows/{id}/approve` | Authorized manager sign-off: approves review draft, marks status completed, logs immutable audit event | `200 OK` |
| `POST` | `/api/v1/workflows/{id}/request-revision` | Request revisions with reviewer instructions: marks status revision_requested, logs audit event | `200 OK` |
| `POST` | `/api/v1/workflows/{id}/resume` | Resume paused or interrupted workflow run from persisted PostgreSQL state | `200 OK` |
| `POST` | `/api/v1/workflows/{id}/cancel` | Cancel an active, pending, or awaiting_approval workflow run | `200 OK` |

### Deterministic Bias & Evidence-Quality Audit Engine (Phase 6)
| Method | Endpoint | Description | Return Status |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/review-cycles/{id}/audit` | Run 5 deterministic audit rules against evidence, feedback, goals, and findings | `200 OK` |
| `POST` | `/api/v1/review-cycles/{id}/bias-audit` | Alias endpoint returning 201 Created with audit summary and generated flags | `201 Created` |
| `GET` | `/api/v1/review-cycles/{id}/audit-flags` | List detected bias & evidence-quality flags (filtering by `status`, `severity`, `flag_type`) | `200 OK` |
| `GET` | `/api/v1/review-cycles/{id}/bias-flags` | Alias endpoint listing bias flags | `200 OK` |
| `PATCH` | `/api/v1/review-cycles/{id}/audit-flags/{flag_id}` | Manager triage & calibration (`open` → `acknowledged`, `resolved`, `not_applicable`) | `200 OK` |
| `GET` | `/api/v1/review-cycles/{id}/audit-summary` | Retrieve overall audit health score (0-100), severity breakdown, and review readiness | `200 OK` |

### Review Analysis & Grounded Performance Insights (Phase 5)
| Method | Endpoint | Description | Return Status |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/review-cycles/{id}/analysis` | Execute evidence-grounded review analysis, persist findings & draft report | `200 OK` |
| `POST` | `/api/v1/review-cycles/{id}/analysis-runs` | Alias endpoint returning 201 Created | `201 Created` |
| `GET` | `/api/v1/review-cycles/{id}/analysis/{analysis_id}` | Retrieve specific analysis by ID with cross-cycle isolation checks | `200 OK` or `404 Not Found` |
| `GET` | `/api/v1/review-cycles/{id}/analysis` | Retrieve latest analysis for the review cycle | `200 OK` or `404 Not Found` |
| `GET` | `/api/v1/review-cycles/{id}/findings` | Retrieve atomic findings (strengths, improvement opportunities, contradictions) | `200 OK` |

### Core Review Workflow (Phase 3)
| Method | Endpoint | Description | Return Status |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/review-cycles` | List review cycles (filtering: `employee_id`, `status`) | `200 OK` |
| `POST` | `/api/v1/review-cycles` | Create review cycle (date validation: `period_end >= period_start`) | `201 Created` |
| `GET` | `/api/v1/review-cycles/{id}` | Fetch review cycle by ID | `200 OK` or `404 Not Found` |
| `PATCH` | `/api/v1/review-cycles/{id}` | Update cycle fields & lifecycle transitions (`draft` → `active` → `in_review` → `completed` → `archived`) | `200 OK`, `409 Conflict`, `422` |
| `DELETE` | `/api/v1/review-cycles/{id}` | Delete review cycle (permitted only in `draft` status) | `204 No Content` or `409 Conflict` |
| `GET` | `/api/v1/feedback` | List feedback (filtering & visibility checks) | `200 OK` |
| `POST` | `/api/v1/feedback` | Submit feedback (`self`, `peer`, `manager`; requires active cycle) | `201 Created`, `409 Conflict`, `422` |
| `GET` | `/api/v1/feedback/{id}` | Fetch feedback by ID (enforces visibility policy) | `200 OK` or `404 Not Found` |
| `PATCH` | `/api/v1/feedback/{id}` | Update feedback content or visibility | `200 OK` |
| `DELETE` | `/api/v1/feedback/{id}` | Delete feedback record | `204 No Content` |
| `GET/POST`| `/api/v1/review-cycles/{id}/feedback` | List or submit feedback directly for a cycle | `200 OK` / `201 Created` |
| `GET` | `/api/v1/goals` | List goals (filtering: `cycle_id`, `employee_id`, `status`) | `200 OK` |
| `POST` | `/api/v1/goals` | Create goal | `201 Created` or `422` |
| `GET` | `/api/v1/goals/{id}` | Fetch goal by ID | `200 OK` or `404 Not Found` |
| `PATCH` | `/api/v1/goals/{id}` | Update goal status, targets, and self-assessment notes | `200 OK` |
| `DELETE` | `/api/v1/goals/{id}` | Delete goal record | `204 No Content` |
| `GET/POST`| `/api/v1/review-cycles/{id}/goals` | List or create goals directly under a cycle | `200 OK` / `201 Created` |

### Evidence Management & Safe Processing (Phase 3 & Phase 4)
| Method | Endpoint | Description | Return Status |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/evidence` | List evidence (filtering: `cycle_id`, `employee_id`, `source_type`, dates, access policies) | `200 OK` |
| `POST` | `/api/v1/evidence` | Register evidence metadata (`pr`, `commit`, `design_doc`, `ticket`, `document_upload`) | `201 Created`, `422` |
| `POST` | `/api/v1/evidence/upload` | Multipart file upload (PDF, DOCX, TXT, CSV), magic signature validation, safe text parsing | `201 Created`, `413`, `422` |
| `GET` | `/api/v1/evidence/{id}` | Fetch evidence by ID (access policy checks: `internal`, `manager_only`, `restricted`, `confidential`) | `200 OK` or `404 Not Found` |
| `GET` | `/api/v1/evidence/{id}/content` | Download or view stored document file (enforces cycle, employee, and role permissions) | `200 OK` or `404 Not Found` |
| `PATCH` | `/api/v1/evidence/{id}` | Update evidence metadata or access policy | `200 OK` |
| `DELETE` | `/api/v1/evidence/{id}` | Delete evidence record and unlink physical storage | `204 No Content` |
| `GET/POST`| `/api/v1/review-cycles/{id}/evidence` | List or register evidence directly under a cycle | `200 OK` / `201 Created` |
| `POST` | `/api/v1/review-cycles/{id}/evidence/upload` | Upload and parse document directly into a review cycle | `201 Created`, `413`, `422` |
| `GET` | `/api/v1/review-cycles/{id}/evidence/completeness` | Cycle evidence completeness score, source distribution, and explicit gap detection | `200 OK` or `404 Not Found` |

### Report Governance, Versioning & Exports (Phase 8 & Phase 9)
| Method | Endpoint | Description | Return Status |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/review-cycles/{id}/report` | Retrieve active report with version and approval metadata | `200 OK` |
| `PATCH` | `/api/v1/reports/{id}/sections/{key}` | Edit section with optimistic concurrency (`base_version_number`) | `200 OK`, `409` |
| `GET` | `/api/v1/reports/{id}/versions` | List immutable report versions | `200 OK` |
| `GET` | `/api/v1/reports/{id}/compare` | Deterministic text and structured list diff engine | `200 OK` |
| `POST` | `/api/v1/reports/{id}/approve` | Version-bound human manager approval | `200 OK`, `409` |
| `POST` | `/api/v1/reports/{id}/request-revision` | Request revisions on active draft | `200 OK` |
| `GET` | `/api/v1/reports/{id}/export/pdf` | Export branded PDF report with dynamic "Page X of Y" | `200 OK` |
| `GET` | `/api/v1/reports/{id}/export/docx` | Export professional Word `.docx` report with styled tables | `200 OK` |

### Performance & Governance Analytics (Phase 9)
| Method | Endpoint | Description | Return Status |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/analytics/overview` | Review totals, mathematical completion rate, health score | `200 OK` |
| `GET` | `/api/v1/analytics/reviews` | Review cycle list and lifecycle status distribution | `200 OK` |
| `GET` | `/api/v1/analytics/evidence` | Evidence source & policy breakdown, cited vs ungrounded claims | `200 OK` |
| `GET` | `/api/v1/analytics/audits` | Deterministic bias flags by rule, severity, and health score distribution | `200 OK` |
| `GET` | `/api/v1/analytics/trends` | Time-bucketed trends (`day`, `week`, `month`) | `200 OK` |

### Foundational Entities (Phase 2)
| Method | Endpoint | Description | Return Status |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/users` | List users (with optional role filter) | `200 OK` |
| `POST` | `/api/v1/users` | Create user (email uniqueness enforced) | `201 Created` |
| `GET` | `/api/v1/users/{user_id}` | Fetch user by ID | `200 OK` or `404 Not Found` |
| `GET` | `/api/v1/teams` | List teams | `200 OK` |
| `POST` | `/api/v1/teams` | Create team (name uniqueness enforced) | `201 Created` |
| `GET` | `/api/v1/teams/{team_id}` | Fetch team by ID | `200 OK` or `404 Not Found` |
| `POST` | `/api/v1/teams/{team_id}/members` | Add user to team | `201 Created` or `409 Conflict` |
| `GET` | `/api/v1/teams/{team_id}/members` | List team memberships | `200 OK` |

---

## 8. Project Documentation

- **[Product Requirements Document (PRD)](file:///Users/kaustubhkadam/Desktop/PERFORMai-360-Fresh/docs/PRD.md)** — Full functional and non-functional requirements.
- **[System Architecture](file:///Users/kaustubhkadam/Desktop/PERFORMai-360-Fresh/docs/ARCHITECTURE.md)** — Architectural design, agent workflow graph, and entity schemas.
- **[Phase Execution Log](file:///Users/kaustubhkadam/Desktop/PERFORMai-360-Fresh/docs/PHASE_LOG.md)** — Live audit log tracking phase completion and verified checks.
