# PERFORMai-360 — End-to-End Demonstration Guide

> **AI-Driven Bias-Aware 360° Performance Evaluation for Software Engineering Teams**  
> **Environment:** macOS Local Development · Port 3000 (Web) · Port 8000 (API) · Port 5433 (PostgreSQL)  
> **Target Audience:** Engineering Leaders, HR Executives, Evaluators, and Technical Reviewers

---

## 1. Important AI Decision-Support Disclaimer

> [!IMPORTANT]
> **PERFORMai-360 is strictly an assistive decision-support platform.**
> - It does **NOT** autonomously make or enforce employment decisions, promotions, compensation adjustments, disciplinary actions, or terminations.
> - An audit flag (e.g., recency bias, ungrounded claim) signifies **"review this statement for factual evidence"**, not proof of wrongdoing or deliberate bias.
> - Final review reports **require human review, calibration, editing, and deliberate approval** by authorized managers.

---

## 2. Demonstration Personas & Authorization Context

Authentication and role-based access control (RBAC) are enforced server-side. In local development and demonstration mode, actor identity is established via request headers:

| Persona | Role | User ID (Example) | Permissions & Scope |
| :--- | :--- | :--- | :--- |
| **Carol Director** | `manager` | `4c81124d-d1c4-431e-83bd-69e780f01441` | Oversees team review cycles; edits drafts, views manager notes, executes human approvals/revisions, exports reports. |
| **Alice Engineer** | `employee` | `b42fe36d-aa2f-4832-b1b7-da9afc376206` | Subject of performance review; submits self-assessments, views employee-scoped reports (confidential notes masked). Cannot approve self. |
| **Bob SRE** | `employee` / `peer` | `e2a1b4c6-8899-44aa-bbcc-112233445566` | Peer reviewer; submits peer feedback. Denied access to Alice's private drafts, versions, and exports. |
| **Dave Manager** | `manager` | `d1e2f3a4-b5c6-47e8-9900-aabbccddeeff` | Engineering manager who is *also* the subject of their own review. Used to demonstrate self-approval prevention. |
| **System Admin** | `admin` | `00000000-0000-0000-0000-000000000001` | Org-wide visibility across all teams, cycles, audit trails, and global analytics. |

---

## 3. Demonstration Prerequisites & Environment Health

### Step 3.1: Verify Services Are Running
Ensure PostgreSQL, FastAPI backend, and Next.js frontend are active:

```bash
# 1. PostgreSQL Docker container (port 5433)
docker compose ps

# 2. Backend Liveness & Readiness Probes
curl -s http://localhost:8000/api/v1/health | jq .
curl -s http://localhost:8000/api/v1/health/ready | jq .

# 3. Frontend Accessibility
curl -s -I http://localhost:3000 | grep "HTTP/1.1 200 OK"
```

Expected output for probes:
```json
{
  "status": "ok",
  "app": "PERFORMai-360",
  "version": "0.1.0",
  "environment": "development"
}
```

---

## 4. Step-by-Step Interactive Walkthrough

### Step 1: Access the Web Dashboard
1. Open your browser to **`http://localhost:3000`**.
2. **Visible Elements:**
   - Sticky navigation header with `Overview`, `Governance`, `Analytics`, and status indicators.
   - Key Guarantees banner: **360° Multi-Source**, **5 Deterministic Rules**, **4 LangGraph Agents**, **100% Human Approval**.
   - Live Backend Health Card displaying PostgreSQL connection state and mock LLM provider status.

---

### Step 2: 360-Degree Feedback & Goal Tracking
Demonstrate multi-source feedback aggregation across self, peer, and manager observations.

```bash
# List review cycles
curl -s "http://localhost:8000/api/v1/review-cycles?limit=5" \
  -H "X-Viewer-Role: manager" \
  -H "X-Viewer-Id: 4c81124d-d1c4-431e-83bd-69e780f01441" | jq .
```

**Workflow Highlights:**
- **Self-Assessments:** Employee submits reflections and goal completions.
- **Peer Observations:** Colleagues submit strengths and collaboration feedback with `shared` or `manager_only` visibility.
- **Manager Feedback:** Evaluator provides guidance and direction.

---

### Step 3: Scoped Evidence Ingestion & Attribution
Demonstrate that findings cite verifiable artifacts rather than hallucinations.

```bash
# Query evidence items linked to the review cycle
curl -s "http://localhost:8000/api/v1/review-cycles/8a49f5aa-49b9-4a94-9f41-859efca5e007/evidence" \
  -H "X-Viewer-Role: manager" | jq .
```

**Key Capabilities:**
- Safe multi-format parsers (PDF, DOCX, TXT, CSV) with binary magic signature validation.
- Access policies: `public`, `internal`, and `manager_only` (restricted evidence is masked for employees).

---

### Step 4: Deterministic Bias & Quality Auditing (5 Explainable Rules)
PERFORMai-360 does not rely on subjective AI prompts to detect bias; it executes 5 deterministic rules:

1. **Recency Bias (`recency_concentration`):** Flags if >60% of cited evidence falls into the final quartile of the review cycle.
2. **Stakeholder Coverage (`stakeholder_coverage`):** Flags if self, peer, or manager viewpoints are absent.
3. **Ungrounded Claims (`evidence_coverage`):** Flags evaluative praise or critique lacking verifiable `evidence_ids`.
4. **Vague Language (`vague_language`):** Flags ambiguous absolutes ("always", "never") and unsupported personality adjectives.
5. **Contradictory Feedback (`contradictions`):** Flags stark sentiment clashes between peer and manager inputs.

```bash
# Run deterministic audit against review cycle
curl -s -X POST "http://localhost:8000/api/v1/review-cycles/8a49f5aa-49b9-4a94-9f41-859efca5e007/audit" \
  -H "X-Viewer-Role: manager" \
  -H "X-Viewer-Id: 4c81124d-d1c4-431e-83bd-69e780f01441" | jq .
```

**UI Demonstration:**
- Scroll to the **Deterministic Bias & Review-Quality Audit Interface** card.
- Observe the **Audit Health Score** (0–100%) and individual flag cards with severity badges (`info`, `warning`, `critical`).

---

### Step 5: LangGraph Multi-Agent Orchestration Engine
Demonstrate the 4-agent state machine coordinating evidence, feedback, bias checks, and draft synthesis:

1. **Evidence Retrieval Agent:** Scopes authorized work records and identifies gaps.
2. **Feedback Analysis Agent:** Groups feedback into themes, strengths, and growth opportunities.
3. **Bias & Quality Auditor:** Computes rule flags and health score.
4. **Review Synthesis Agent:** Drafts grounded executive summary and citations.
5. **Human Approval Pause Boundary:** State machine halts automatically in `awaiting_approval`.

**UI Action:**
- Scroll to the **Multi-Agent Review Orchestration Engine** (`#orchestration`).
- Observe the 5 stage cards: `EvidenceRetrieval`, `FeedbackAnalysis`, `BiasAuditorAgent`, `ReviewSynthesis`, and the pulsating amber `Human Approval Pause` node.

---

### Step 6: Section-Level Editing & Optimistic Concurrency
Managers can refine specific draft sections without losing underlying AI citations or risking lost updates.

```bash
# Edit executive summary with optimistic concurrency protection (base_version_number=1)
curl -s -X POST "http://localhost:8000/api/v1/reports/056659f2-6bd4-49bc-a686-6388a62756b0/sections/executive_summary" \
  -H "Content-Type: application/json" \
  -H "X-Viewer-Role: manager" \
  -H "X-Viewer-Id: 4c81124d-d1c4-431e-83bd-69e780f01441" \
  -d '{
    "content": "Alice demonstrated exemplary technical leadership in distributed caching overhaul.",
    "reason": "Clarified cross-datacenter scope after architectural review",
    "base_version_number": 1
  }' | jq .
```

**Expected Outcome:**
- Version increments from `1` to `2`.
- A new immutable snapshot is recorded in `report_versions`.
- An audit event (`report.section_edited`) is written to `audit_events`.

---

### Step 7: Human Manager Review Decision (Approval vs Revision)
Demonstrate the human-in-the-loop sign-off requirement:

#### Option A: Approve Report
```bash
curl -s -X POST "http://localhost:8000/api/v1/reports/056659f2-6bd4-49bc-a686-6388a62756b0/approve" \
  -H "Content-Type: application/json" \
  -H "X-Viewer-Role: manager" \
  -H "X-Viewer-Id: 4c81124d-d1c4-431e-83bd-69e780f01441" \
  -d '{
    "version_number": 2,
    "comments": "Final review approved following calibration committee alignment."
  }' | jq .
```

#### Option B: Request Revision
```bash
curl -s -X POST "http://localhost:8000/api/v1/reports/056659f2-6bd4-49bc-a686-6388a62756b0/request-revision" \
  -H "Content-Type: application/json" \
  -H "X-Viewer-Role: manager" \
  -H "X-Viewer-Id: 4c81124d-d1c4-431e-83bd-69e780f01441" \
  -d '{
    "version_number": 2,
    "comments": "Please include performance benchmarks for the Kafka cluster migration."
  }' | jq .
```

---

### Step 8: Deterministic Version History & Diff Comparison
Demonstrate transparent version inspection:

1. In the **Human Approval, Versioning & Governance** card, click **Version History**.
2. Compare Version 1 and Version 2:
   - Click **Deterministic Version Diff**.
   - Select Base Version `1` and Target Version `2`.
   - Observe unified text diffs (`+` additions, `-` deletions) and structured changes.

```bash
# API Version Comparison
curl -s "http://localhost:8000/api/v1/reports/056659f2-6bd4-49bc-a686-6388a62756b0/compare?from_version=1&to_version=2" \
  -H "X-Viewer-Role: manager" \
  -H "X-Viewer-Id: 4c81124d-d1c4-431e-83bd-69e780f01441" | jq .
```

---

### Step 9: Real-Time Analytics & WCAG Data Tables
1. Scroll to the **Performance & Governance Analytics Dashboard** (`#analytics`).
2. **Review Metrics:**
   - **Total Review Cycles** and **Completion Rate** (with tooltip defining exact formula).
   - **Lifecycle Distribution** (BarChart).
   - **Evidence Distribution** (Donut PieChart).
   - **Bias Findings by Rule** (BarChart).
   - **Activity Trends** (Stacked AreaChart).
3. **Accessibility Demonstration:**
   - Click the button **Show Accessible Tables (WCAG)** (`aria-pressed="true"`).
   - Observe full HTML5 tabular fallbacks (`<table>`, `<caption>`, `<th scope="col">`) rendered for screen readers and high-contrast accessibility.

---

### Step 10: Multi-Format Reports Export (PDF & DOCX)
Demonstrate downloading branded, version-pinned evaluation documents:

1. Click **Export PDF** or **Export DOCX** in the Governance card header.
2. Verify document contents:
   - **Draft Notice:** Unapproved drafts carry prominent watermarks: `"DRAFT REPORT — NOT APPROVED OR FINALIZED"`.
   - **Approved Notice:** Final reports display immutable manager approval credentials, decision timestamp, and comments.
   - **Confidential Masking:** If downloaded with `X-Viewer-Role: employee`, manager succession notes (`reviewer_notes`) are completely omitted.

```bash
# Download PDF export to local file
curl -s "http://localhost:8000/api/v1/reports/056659f2-6bd4-49bc-a686-6388a62756b0/export/pdf?version_number=1" \
  -H "X-Viewer-Role: manager" \
  -H "X-Viewer-Id: 4c81124d-d1c4-431e-83bd-69e780f01441" \
  -o /tmp/alice_review_v1.pdf

# Check PDF magic header
head -c 5 /tmp/alice_review_v1.pdf
# Expected output: %PDF-
```

---

### Step 11: Security & Boundary Defenses Demo

#### 1. Privilege Escalation Defeat (Header Precedence)
An employee passing `?viewer_role=admin` is strictly evaluated as `employee`:

```bash
curl -s "http://localhost:8000/api/v1/analytics/overview?viewer_role=admin" \
  -H "X-Viewer-Role: employee" \
  -H "X-Viewer-Id: b42fe36d-aa2f-4832-b1b7-da9afc376206" | jq .
# Result: Returns only Alice's single review cycle, NOT global admin data.
```

#### 2. Cross-Employee Isolation (HTTP 404)
Bob cannot view or export Alice's review:

```bash
curl -s -i "http://localhost:8000/api/v1/reports/056659f2-6bd4-49bc-a686-6388a62756b0" \
  -H "X-Viewer-Role: employee" \
  -H "X-Viewer-Id: e2a1b4c6-8899-44aa-bbcc-112233445566" | grep "HTTP/1.1 404"
# Result: HTTP/1.1 404 Not Found
```

#### 3. Manager Self-Approval Block (HTTP 403)
Dave (manager) cannot approve his own review cycle:

```bash
curl -s -X POST "http://localhost:8000/api/v1/reports/056659f2-6bd4-49bc-a686-6388a62756b0/approve" \
  -H "Content-Type: application/json" \
  -H "X-Viewer-Role: manager" \
  -H "X-Viewer-Id: b42fe36d-aa2f-4832-b1b7-da9afc376206" \
  -d '{"version_number": 1, "comments": "Self approval attempt"}' | jq .
# Result: HTTP 403 Forbidden ("Employees cannot approve their own performance reviews.")
```

---

## 5. Demonstration Recovery & Database Reset

All automated tests utilize transactional rollback fixtures (`NullPool` async engine) ensuring zero persistent contamination of the development database. If you wish to re-seed demo data:

```bash
# Verify Alembic migration head
cd backend
source .venv/bin/activate
alembic current
alembic check
```
