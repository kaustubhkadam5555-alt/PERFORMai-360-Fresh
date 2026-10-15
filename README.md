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

- **Frontend:** Next.js (App Router), React 19, TypeScript, Tailwind CSS, shadcn/ui, Recharts
- **Backend:** Python 3.14+, FastAPI, Pydantic v2, SQLAlchemy (asyncpg), Alembic
- **Database:** PostgreSQL 16+ (Docker Compose)
- **Agent Orchestration:** LangGraph state machine with deterministic approval pauses
- **AI Integration:** Provider-neutral adapter with offline mock support (no paid API key required for MVP)
- **Testing:** pytest (backend), Vitest (frontend), Playwright (E2E)

---

## 3. Verified Local Development Environment

| Requirement | Supported Version (Tested) | Notes |
| :--- | :--- | :--- |
| **Operating System** | macOS 14+ | Development & demonstration target |
| **Python** | 3.14.7 | Virtual environments via `venv` |
| **Node.js** | v26.9.0 | Frontend runtime |
| **npm** | 12.2.0 | Frontend package management |
| **Docker Compose** | v5.5.1 | Local PostgreSQL service |
| **Git** | 2.55.0+ | Version control |

---

## 4. Repository Layout

```text
PERFORMai-360-Fresh/
├── apps/
│   └── web/                    # Next.js frontend application (Phase 1+)
├── backend/
│   ├── app/                    # FastAPI application and services (Phase 1+)
│   │   ├── api/                # API route controllers
│   │   ├── core/               # Configuration, security, logging
│   │   ├── db/                 # Database engine and sessions
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic
│   │   ├── agents/             # Agent nodes
│   │   └── workflows/          # LangGraph orchestration
│   ├── migrations/             # Alembic database migrations (Phase 2+)
│   ├── tests/                  # Backend pytest test suite (Phase 1+)
│   └── pyproject.toml
├── docs/
│   ├── PRD.md                  # Comprehensive Product Requirements Document
│   ├── ARCHITECTURE.md         # Detailed System Architecture Specification
│   └── PHASE_LOG.md            # Chronological execution log & audit trail
├── scripts/                    # Utility and synthetic data seeding scripts (Phase 2+)
├── .env.example                # Configuration template with placeholders only
├── .gitignore                  # Git ignore rules for macOS, Python, Node, secrets
└── README.md                   # Project overview and instructions
```

---

## 5. Phased Implementation Roadmap

Development proceeds strictly in sequential phases:

- [x] **Phase 0 — Repository and Planning Baseline** *(Completed)*
- [ ] **Phase 1 — Application Skeleton & Local Developer Environment**
- [ ] **Phase 2 — Database, Migrations, and Authentication**
- [ ] **Phase 3 — Core Review Workflow**
- [ ] **Phase 4 — Evidence Processing & Retrieval**
- [ ] **Phase 5 — Single-Pass AI Analysis & Grounded Report Draft**
- [ ] **Phase 6 — Bias & Evidence-Quality Audit Engine**
- [ ] **Phase 7 — LangGraph Multi-Agent Orchestration**
- [ ] **Phase 8 — Human Approval, Report Versions, & Governance**
- [ ] **Phase 9 — Dashboard Polish, Accessibility, & Export**
- [ ] **Phase 10 — Comprehensive Testing & Security Review**
- [ ] **Phase 11 — Final Documentation & Demonstration Readiness**

Refer to [docs/PHASE_LOG.md](file:///Users/kaustubhkadam/Desktop/PERFORMai-360-Fresh/docs/PHASE_LOG.md) for detailed milestone records.

---

## 6. Quick Start (Phase 0 Baseline)

### 1. Clone & Configuration
```bash
# Clone the repository
git clone https://github.com/kaustubhkadam5555-alt/PERFORMai-360-Fresh.git
cd PERFORMai-360-Fresh

# Copy the environment template (placeholders only)
cp .env.example .env
```

### 2. Security & Secrets Disclaimer
- Never commit `.env` or any production credentials to version control.
- All secrets, API keys, and private certificates are strictly excluded via `.gitignore`.
- Demos use synthetic data exclusively.

---

## 7. Project Documentation

- **[Product Requirements Document (PRD)](file:///Users/kaustubhkadam/Desktop/PERFORMai-360-Fresh/docs/PRD.md)** — Full functional and non-functional requirements.
- **[System Architecture](file:///Users/kaustubhkadam/Desktop/PERFORMai-360-Fresh/docs/ARCHITECTURE.md)** — Architectural design, agent workflow graph, and entity schemas.
- **[Phase Execution Log](file:///Users/kaustubhkadam/Desktop/PERFORMai-360-Fresh/docs/PHASE_LOG.md)** — Live audit log tracking phase completion and verified checks.
