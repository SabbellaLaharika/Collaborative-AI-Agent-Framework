import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db.init_db import init_db
from src.api.router import router as tasks_router
from src.api.websocket import ws_router

logger = logging.getLogger(__name__)

tags_metadata = [
    {
        "name": "Tasks",
        "description": "Endpoints to submit prompts, check multi-agent task execution status, and provide Human-in-the-Loop approval.",
    },
    {
        "name": "WebSockets",
        "description": "Real-time WebSocket streaming endpoints for task status updates via Redis Pub/Sub.",
    },
    {
        "name": "System",
        "description": "Healthcheck and container diagnostics.",
    },
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to initialize database on app startup."""
    try:
        init_db()
        logger.info("Database initialized successfully on API startup.")
    except Exception as e:
        logger.error(f"Failed to initialize database on API startup: {e}")
    yield

app = FastAPI(
    title="Collaborative AI Agent Orchestration Framework",
    description=(
        "An asynchronous multi-agent system powered by **LangGraph**, **FastAPI**, **Celery**, **PostgreSQL**, **Redis**, and **WebSockets**.\n\n"
        "### Features:\n"
        "- **POST /api/v1/tasks**: Submit a prompt to start asynchronous research & writing agents.\n"
        "- **GET /api/v1/tasks/{task_id}**: Retrieve real-time task status, agent audit logs, and final comparison summary.\n"
        "- **POST /api/v1/tasks/{task_id}/approve**: Human-in-the-Loop approval endpoint to resume paused workflows.\n"
        "- **ws://localhost:8000/ws/tasks/{task_id}**: Live WebSocket status stream via Redis Pub/Sub.\n"
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
    swagger_ui_parameters={"deepLinking": True, "displayRequestDuration": True},
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", status_code=200, tags=["System"], summary="Root Health Check")
def root_check():
    """Root endpoint returning system health status."""
    return {"status": "ok"}

@app.get("/health", status_code=200, tags=["System"], summary="Container Health Check")
def health_check():
    """Health check endpoint required by Docker Compose service health checks."""
    return {"status": "ok"}

app.include_router(tasks_router)
app.include_router(ws_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
