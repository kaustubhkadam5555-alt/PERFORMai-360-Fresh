# PERFORMai-360 Backend (FastAPI)

FastAPI application providing REST endpoints, evaluation workflow orchestration, domain services, repositories, and database persistence for **PERFORMai-360**.

---

## 1. Directory Structure

```text
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── health.py         # Liveness and readiness probes
│   │       │   ├── users.py          # User management endpoints
│   │       │   ├── teams.py          # Team & membership endpoints
│   │       │   ├── review_cycles.py  # Review cycle workflow & nested endpoints
│   │       │   ├── feedback.py       # 360-degree feedback management
│   │       │   ├── goals.py          # Goal tracking & progress management
│   │       │   └── evidence.py       # Evidence upload, retrieval & access policy management
│   │       └── router.py             # API v1 router aggregator
│   ├── core/
│   │   └── config.py                 # Pydantic Settings configuration (upload limits, storage dir)
│   ├── db/
│   │   ├── base.py                   # SQLAlchemy 2.0 Base, naming conventions & mixins
│   │   └── session.py                # Async SQLAlchemy engine, session generator & health probe
│   ├── models/                       # SQLAlchemy 2.0 ORM domain entities (13 PRD models)
│   ├── parsers/                      # Safe document parsers (PDF, DOCX, TXT, CSV) & magic signature validation
│   ├── schemas/                      # Pydantic v2 validation & serialization schemas
│   ├── repositories/                 # Repository layer (DB queries & mutations)
│   ├── services/                     # Business logic, lifecycle, parsing & evidence services
│   └── main.py                       # FastAPI application entry point, CORS & lifespan
├── migrations/                       # Alembic async migration scripts & env.py
├── tests/                            # Pytest test suite (64 automated tests, 100% pass)
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
| `GET` | `/health/ready` | Readiness check (PostgreSQL reachable) | `200 OK` (healthy) or `503` |
| `GET` | `/api/v1/health` | Mounted v1 liveness check | `200 OK` |
| `GET` | `/api/v1/health/ready` | Mounted v1 readiness check | `200 OK` or `503` |
| `GET` | `/docs` | Interactive Swagger API docs | `200 OK` |

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
