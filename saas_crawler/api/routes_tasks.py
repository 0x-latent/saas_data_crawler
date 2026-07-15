"""Crawler task routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from saas_crawler.storage.db import get_session
from saas_crawler.storage.models import CrawlerTask
from saas_crawler.storage.repositories import create_task, update_task_status
from saas_crawler.tasks.queue import enqueue_task

from .serializers import model_to_dict


router = APIRouter(tags=["tasks"])


class TaskCreate(BaseModel):
    platform: str
    task_type: str
    account_id: int | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    run_now: bool = False


@router.post("/tasks")
def create_crawler_task(payload: TaskCreate, session: Session = Depends(get_session)):
    task = create_task(
        session,
        platform=payload.platform,
        task_type=payload.task_type,
        account_id=payload.account_id,
        params=payload.params,
    )
    session.commit()
    if payload.run_now:
        from saas_crawler.tasks.task_runner import run_task

        run_task(task.id)
        task = session.get(CrawlerTask, task.id)
    else:
        try:
            job = enqueue_task(task.id)
            task.log_tail = f"Queued job {job.id}"
            session.commit()
        except Exception as exc:
            task.log_tail = f"Task created but not queued: {exc}"
            session.commit()
    return model_to_dict(task)


@router.get("/tasks")
def list_tasks(session: Session = Depends(get_session)):
    tasks = session.scalars(select(CrawlerTask).order_by(desc(CrawlerTask.created_at)).limit(200)).all()
    return [model_to_dict(task) for task in tasks]


@router.get("/tasks/{task_id}")
def get_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(CrawlerTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return model_to_dict(task)


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(CrawlerTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    update_task_status(session, task, status="cancelled", log_tail=f"{task.log_tail}\nCancel requested.")
    session.commit()
    return model_to_dict(task)
