"""RQ queue helpers."""

from __future__ import annotations

from redis import Redis
from rq import Queue

from saas_crawler.storage import settings


QUEUE_NAME = "crawler"
LOGIN_QUEUE_NAME = "login"


def get_queue() -> Queue:
    redis = Redis.from_url(settings.REDIS_URL)
    return Queue(QUEUE_NAME, connection=redis)


def enqueue_task(task_id: int):
    queue = get_queue()
    return queue.enqueue("saas_crawler.tasks.task_runner.run_task", task_id, job_timeout="6h")


def enqueue_login_session(login_session_id: int):
    redis = Redis.from_url(settings.REDIS_URL)
    queue = Queue(LOGIN_QUEUE_NAME, connection=redis)
    return queue.enqueue(
        "saas_crawler.accounts.login_runner.run_login_session",
        login_session_id,
        job_timeout="15m",
    )
