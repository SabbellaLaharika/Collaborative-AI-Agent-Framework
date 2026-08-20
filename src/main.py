import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db.init_db import init_db
from src.api.router import router as tasks_router
from src.api.websocket import ws_router

logger = logging.getLogger(__name__)

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
    description="Asynchronous multi-agent system powered by LangGraph, FastAPI, Celery, PostgreSQL, Redis, and WebSockets.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", status_code=200)
def health_check():
    """Health check endpoint required by Docker Compose service health checks."""
    return {"status": "ok"}

app.include_router(tasks_router)
app.include_router(ws_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
