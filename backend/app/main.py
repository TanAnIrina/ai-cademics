"""AI-cademics backend application entrypoint.

Wires together the routers, configures CORS for the frontend, initialises the
database and seeds demo classrooms on startup.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import SessionLocal, init_db
from .routers import agent, auth, chat, classrooms, history
from .seed import seed_classrooms


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_classrooms(db)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI-cademics",
        description=(
            "Multi-agent classroom simulation. A teacher agent and two student "
            "agents run timed learning sprints; observers watch live and chat."
        ),
        version="2.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(classrooms.router)
    app.include_router(chat.router)
    app.include_router(history.router)
    app.include_router(agent.router)

    @app.get("/")
    def root():
        return {"name": "AI-cademics", "version": "2.0.0", "docs": "/docs"}

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
