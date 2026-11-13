# MeetingMind

[![CI Pipeline](https://github.com/Soulofghost/meetingmind/actions/workflows/ci.yml/badge.svg)](https://github.com/Soulofghost/meetingmind/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Database](https://img.shields.io/badge/SQLite-WAL%20Mode-003B57.svg)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **MeetingMind** is an enterprise-grade meeting intelligence, summarization, and action-tracking platform. It ingests multi-speaker transcripts, extracts verified strategic decisions, detects assignable action items with due dates and priority scores, and computes participant talk-time and tone analytics.

---

## 1. System Architecture

MeetingMind is built on a clean three-tier architecture decoupling natural language dialogue parsing, relational extraction indexing, and an executive-grade frontend.

```
┌─────────────────────────────────────────────────────────────┐
│                   Executive UI (SPA)                        │
│   • Metric Ribbon (KPIs)       • Dynamic Tab Navigator      │
│   • Interactive Ingestion      • Action Item Workflow       │
│   • Speaker Talk-Time Charts   • Decision Ledger & Export   │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON
┌──────────────────────────────▼──────────────────────────────┐
│                   FastAPI Application Tier                  │
│   • Ingestion & CRUD Routers   • Lifespan State Handler     │
│   • Task Status State-Machine  • Cross-Origin Security      │
└──────────────────────────────┬──────────────────────────────┘
                               │
       ┌───────────────────────┴───────────────────────┐
       ▼                                               ▼
┌─────────────────────────────┐         ┌─────────────────────────────┐
│  NLP Extraction Pipeline    │         │  High-Performance Database  │
│  • Dialogue Turn Parser     │         │  • SQLite 3 with WAL Mode   │
│  • Action Item Extractor    │         │  • Foreign Key Cascade      │
│  • Decision Ledger Engine   │         │  • Indices on Foreign Keys  │
│  • Speaker Voice Analytics  │         │  • Shared-Memory Test Mode  │
│  • Executive Synthesizer    │         └─────────────────────────────┘
└─────────────────────────────┘
```

---

## 2. Key Capabilities

### A. Resilient Transcript Parser
Normalizes meeting dialogues across arbitrary transcript styles:
- `[00:01:23] Alice: Welcome everyone...`
- `Alice (00:01:23): Welcome everyone...`
- `00:01:23 - Bob: We should proceed...`
- `Charlie: I will deploy the build...`
- Auto-handles multi-line turn overflows and anonymous speaker fallbacks.

### B. Action Item Extraction Engine
- **Syntactic Triggers:** Detects explicit markers (`Action Item:`, `TODO:`) as well as modal commitment phrasing (`I will...`, `Marcus will...`, `Let's make sure to...`).
- **Assignee Resolution:** Maps actions to either the speaker or third-party named participants.
- **Deadline Extractor:** Parses temporal expressions (`by Friday`, `before Q3`, `next week`, `EOD`).
- **Priority & Confidence:** Evaluates urgency tokens (`critical`, `blocker`, `urgent` -> `HIGH`) and computes heuristic confidence metrics.

### C. Ratified Decision Ledger
Isolates strategic consensus statements (`We decided to adopt...`, `Approved the $250k budget...`, `Agreed to...`) and categorizes them into Architectural, Strategic, Budgetary, Operational, or Governance records.

### D. Speaker Analytics & Sentiment Dynamics
Quantifies meeting participation:
- Word share and estimated talk-time percentages.
- Turn frequencies.
- Sentiment tone scoring (`Constructive / Collaborative`, `Critical / Risk-Focused`, `Urgent / Focused`, `Objective / Neutral`).

### E. Action Item Lifecycle Management
Interactive status workflow (`PENDING` -> `IN_PROGRESS` -> `COMPLETED`) with RESTful PATCH endpoints and audit logging.

---

## 3. Technology Stack

| Layer | Component | Description |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI 0.110+ | Asynchronous RESTful API engine |
| **Language Runtime** | Python 3.11+ | Modern type annotations & pattern matching |
| **Data Validation** | Pydantic v2 | Strict JSON schema serialization and validation |
| **Database** | SQLite 3 | WAL mode enabled with foreign key integrity |
| **Frontend** | Vanilla JS / CSS3 | Bespoke executive boardroom theme with glassmorphic cards |
| **Testing** | Pytest + HTTPX | Automated unit and integration testing suite |
| **DevOps** | Docker / Compose | Multi-stage lightweight deployment container |
| **CI/CD** | GitHub Actions | Automated build, test, and lint validation |

---

## 4. API Endpoints

### Ingestion & Synthesis
- `POST /api/meetings/process` — Ingest raw transcript and run full extraction pipeline.
- `GET /api/meetings` — Retrieve archived sessions (supports `?q=` search filter).
- `GET /api/meetings/{id}` — Fetch detailed meeting breakdown (turns, actions, decisions, speakers).
- `DELETE /api/meetings/{id}` — Cascade delete meeting session.

### Action Items Workflow
- `PATCH /api/meetings/{meeting_id}/action-items/{action_id}` — Update item status (`PENDING`, `COMPLETED`), priority, or assignee.
- `POST /api/meetings/{meeting_id}/action-items` — Append manual action item to session.

### Executive Overview & Health
- `GET /api/meetings/analytics/overview` — Aggregated KPIs (total sessions, decision counts, completion rate).
- `GET /health` — Service readiness and liveness check.

---

## 5. Local Development & Testing

### Prerequisites
- Python 3.11+
- Virtual environment tool (`venv` or `uv`)

### Installation
```bash
# Clone the repository
git clone https://github.com/Soulofghost/meetingmind.git
cd meetingmind

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
```

### Running the Application
```bash
# Start backend server
uvicorn app.main:app --app-dir backend --reload --port 8000
```
Visit `http://localhost:8000` to interact with the executive interface.

### Running Test Suite
```bash
pytest backend/tests -v
```

---

## 6. Docker Deployment

```bash
# Build and launch with Docker Compose
docker-compose up --build -d

# Check service logs
docker-compose logs -f
```

---

## 7. License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
