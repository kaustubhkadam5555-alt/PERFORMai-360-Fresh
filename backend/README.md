# PERFORMai-360 Backend (FastAPI)

FastAPI application providing REST endpoints, authentication, evaluation workflow orchestration, and database access for **PERFORMai-360**.

---

## 1. Directory Structure

```text
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   └── health.py    # Liveness and readiness endpoints
│   │       └── router.py        # API v1 router aggregator
│   ├── core/
│   │   └── config.py            # Pydantic Settings configuration
│   ├── db/
│   │   └── session.py           # Async SQLAlchemy engine & health probe
│   └── main.py                  # Application entry point & CORS
├── tests/
│   ├── conftest.py              # Pytest fixtures & async client
│   └── test_health.py           # Unit & readiness probe tests
└── pyproject.toml               # Dependency specifications & tool configs
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

### Run the Development Server
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Run Automated Tests
```bash
pytest -v
```

---

## 3. Health & Readiness Probes

| Method | Endpoint | Description | Expected Status |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Liveness check (process up) | `200 OK` |
| `GET` | `/health/ready` | Readiness check (PostgreSQL reachable) | `200 OK` (healthy) or `503 Service Unavailable` |
| `GET` | `/api/v1/health` | Mounted v1 liveness check | `200 OK` |
| `GET` | `/api/v1/health/ready` | Mounted v1 readiness check | `200 OK` or `503` |
| `GET` | `/docs` | Interactive Swagger API docs | `200 OK` |
