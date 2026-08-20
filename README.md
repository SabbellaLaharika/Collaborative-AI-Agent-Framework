# Collaborative AI Agent Orchestration Framework with LangGraph

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Celery](https://img.shields.io/badge/Celery-Async--Worker-3775A9.svg)](https://docs.celeryq.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)

An asynchronous, production-grade multi-agent orchestration backend where specialized AI agents (`ResearchAgent` and `WritingAgent`) collaborate using **LangGraph**, **FastAPI**, **Celery**, **PostgreSQL**, **Redis**, and **WebSockets**, featuring native **Human-in-the-Loop (HITL)** capabilities and resilient fault-tolerance.

---

## 🏗️ System Architecture

```
                               ┌─────────────────────────┐
                               │     FastAPI Gateway     │
                               │  POST /api/v1/tasks     │
                               └───────────┬─────────────┘
                                           │ Dispatches Task
                                           ▼
┌──────────────────┐  Publishes Status  ┌─────────────────┐
│ WebSocket Client ◄────────────────────┤  Redis Pub/Sub  │
└──────────────────┘                    └────────▲────────┘
                                                 │ Updates Status
                                                 │
                                        ┌────────┴────────┐
                                        │  Celery Worker  │
                                        └────────┬────────┘
                                                 │ Orchestrates
                                                 ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             LangGraph Multi-Agent Graph                          │
│                                                                                  │
│   ┌─────────────────┐      Writes      ┌─────────────────────────┐               │
│   │ ResearchAgent   ├─────────────────►│ Redis Shared Scratchpad │               │
│   └────────┬────────┘                  │ task:<task_id>:workspace│               │
│            │ Passes State              └────────────┬────────────┘               │
│            ▼                                        │ Reads                      │
│   ┌─────────────────┐                               │ Findings                   │
│   │ WritingAgent    ◄───────────────────────────────┘                            │
│   └────────┬────────┘                                                            │
│            │ Pauses Execution                                                    │
│            ▼                                                                     │
│   ┌───────────────────────────┐   Resumes on /approve   ┌────────────────────┐   │
│   │ AWAITING_APPROVAL Checkpoint├───────────────────────►│ Finalize & Save DB │   │
│   └───────────────────────────┘                         └────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Features

* **Containerized Architecture**: Single-command startup via `docker-compose up --build` managing `api`, `worker`, `db` (PostgreSQL 15), and `redis` with container health checks.
* **LangGraph Multi-Agent StateGraph**: Sequential collaborative graph routing tasks from `ResearchAgent` to `WritingAgent`.
* **Human-in-the-Loop (HITL)**: Pauses execution at `AWAITING_APPROVAL` checkpoint and resumes execution seamlessly when `/api/v1/tasks/{task_id}/approve` is invoked.
* **Ephemeral Shared Redis Workspace**: Fast in-memory scratchpad (`task:<task_id>:workspace`) for intermediate findings transfer between agents without clogging PostgreSQL.
* **Real-time Status WebSockets**: Asynchronous streaming via `/ws/tasks/{task_id}` powered by Redis Pub/Sub (`task:<task_id>:status`).
* **Fault Tolerance & Flaky Tool Retry**: Integrated `@retry` wrapper handling simulated network timeouts for `__FLAKY_TEST__` without failing graph execution.
* **Machine-Readable Structured Logging**: Line-by-line JSON activity tracking written to `logs/agent_activity.log` for auditability.

---

## 🛠️ Environment Configuration (`.env.example`)

Copy `.env.example` to `.env`:

```env
# LLM Provider Configuration
LLM_API_KEY="sk-your-provider-key"

# PostgreSQL Database
DATABASE_URL="postgresql://user:password@db:5432/agent_db"

# Redis Cache & Message Broker
REDIS_URL="redis://redis:6379/0"
CELERY_BROKER_URL="redis://redis:6379/1"
CELERY_RESULT_BACKEND="redis://redis:6379/2"

# Application Configuration
API_PORT="8000"
```

---

## ⚡ Quickstart with Docker Compose

Launch the complete backend ecosystem:

```bash
docker-compose up --build
```

Verify service status:

```bash
docker-compose ps
```

All 4 services (`agent_db`, `agent_redis`, `agent_api`, `agent_worker`) will initialize and become healthy automatically.

---

## 📡 REST API & WebSocket Reference

### 1. Healthcheck
* **`GET /health`**
  * Response: `200 OK` `{"status": "ok"}`

### 2. Create Agent Task
* **`POST /api/v1/tasks`**
  * Request Body:
    ```json
    {
      "prompt": "Research the key features of LangGraph and CrewAI. Write a short comparison summary for a technical audience."
    }
    ```
  * Response (`202 Accepted`, <500ms):
    ```json
    {
      "task_id": "123e4567-e89b-12d3-a456-426614174000",
      "status": "PENDING"
    }
    ```

### 3. Get Task Status & Audit Trail
* **`GET /api/v1/tasks/{task_id}`**
  * Response (`200 OK`):
    ```json
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "prompt": "Research the key features of LangGraph and CrewAI...",
      "status": "AWAITING_APPROVAL",
      "result": null,
      "agent_logs": [
        {
          "agent": "ResearchAgent",
          "action": "Searching for LangGraph features",
          "timestamp": "2026-08-19T20:00:05Z"
        },
        {
          "agent": "WritingAgent",
          "action": "Drafting comparison summary",
          "timestamp": "2026-08-19T20:01:15Z"
        }
      ],
      "created_at": "2026-08-19T20:00:00Z",
      "updated_at": "2026-08-19T20:01:15Z"
    }
    ```

### 4. Human Approval (HITL Resume)
* **`POST /api/v1/tasks/{task_id}/approve`**
  * Request Body:
    ```json
    {
      "approved": true,
      "feedback": "Looks great! Ready to finalize."
    }
    ```
  * Response (`200 OK`):
    ```json
    {
      "task_id": "123e4567-e89b-12d3-a456-426614174000",
      "status": "RESUMED"
    }
    ```

### 5. Real-Time Status Streaming (WebSocket)
* **`ws://localhost:8000/ws/tasks/{task_id}`**
  * Pushed Messages:
    ```json
    {
      "task_id": "123e4567-e89b-12d3-a456-426614174000",
      "status": "RUNNING"
    }
    ```

---

## 🧪 Running Automated Tests

Run the complete test suite:

```bash
python -m pytest tests/
```

```
collected 9 items

tests/test_api.py ....                                                   [ 44%]
tests/test_websocket.py .                                                [ 55%]
tests/test_workflow.py ....                                              [100%]

============================== 9 passed in 0.43s ==============================
```

---

## 📁 Repository Structure

```
.
├── docker-compose.yml       # Service orchestration (api, worker, db, redis)
├── Dockerfile               # Application container blueprint
├── .env.example             # Environment template
├── README.md                # System documentation
├── requirements.txt         # Dependencies
├── pytest.ini               # Test configuration
├── logs/
│   └── agent_activity.log   # Machine-readable JSON activity audit file
├── src/
│   ├── main.py              # FastAPI application entrypoint
│   ├── api/                 # REST & WebSocket routes and Pydantic schemas
│   ├── worker/              # Celery background tasks & app instance
│   ├── agents/              # LangGraph workflow, nodes, tools & workspace
│   ├── db/                  # PostgreSQL connection pool & SQLAlchemy models
│   └── config/              # Centralized settings & Redis client
└── tests/                   # Automated pytest suite
```
