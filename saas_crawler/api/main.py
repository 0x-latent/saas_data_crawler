"""FastAPI entrypoint for the crawler service."""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from saas_crawler.storage import settings
from saas_crawler.storage.db import get_session, init_database
from saas_crawler.storage.repositories import dashboard_counts

from .routes_accounts import router as accounts_router
from .routes_assets import router as assets_router
from .routes_creators import router as creators_router
from .routes_tasks import router as tasks_router


app = FastAPI(title="SaaS Data Crawler API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    if settings.AUTO_CREATE_TABLES:
        init_database()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dashboard")
def dashboard(session: Session = Depends(get_session)):
    return dashboard_counts(session)


app.include_router(assets_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(accounts_router, prefix="/api")
app.include_router(creators_router, prefix="/api")
