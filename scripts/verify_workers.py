"""Verify RQ executes login jobs and respects pre-cancelled crawler tasks."""

from __future__ import annotations

import sys
from pathlib import Path

from redis import Redis
from rq import Queue, SimpleWorker
from sqlalchemy import delete

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from saas_crawler.storage import settings  # noqa: E402
from saas_crawler.storage.db import SessionLocal  # noqa: E402
from saas_crawler.storage.models import Account, AccountSecret, CrawlerTask, LoginSession  # noqa: E402
from saas_crawler.storage.repositories import create_account, create_login_session, create_task  # noqa: E402
from saas_crawler.tasks.queue import LOGIN_QUEUE_NAME, QUEUE_NAME  # noqa: E402


def main() -> int:
    redis = Redis.from_url(settings.REDIS_URL)
    account_id: int | None = None
    login_session_id: int | None = None
    task_id: int | None = None
    jobs = []
    try:
        with SessionLocal() as session:
            account = create_account(
                session,
                platform="unsupported_validation_platform",
                display_name="__worker_validation__",
                login_type="qr",
            )
            account_id = account.id
            login_session = create_login_session(session, account=account, mode="qr")
            login_session_id = login_session.id
            task = create_task(
                session,
                platform="xingtu",
                task_type="author_square",
                account_id=account.id,
                params={"max_pages": 1},
            )
            task.status = "cancelled"
            task_id = task.id
            session.commit()

        login_queue = Queue(LOGIN_QUEUE_NAME, connection=redis)
        crawler_queue = Queue(QUEUE_NAME, connection=redis)
        jobs.append(login_queue.enqueue("saas_crawler.accounts.login_runner.run_login_session", login_session_id))
        jobs.append(crawler_queue.enqueue("saas_crawler.tasks.task_runner.run_task", task_id))
        SimpleWorker([LOGIN_QUEUE_NAME], connection=redis).work(burst=True, logging_level="WARNING")
        SimpleWorker([QUEUE_NAME], connection=redis).work(burst=True, logging_level="WARNING")

        with SessionLocal() as session:
            login_session = session.get(LoginSession, login_session_id)
            task = session.get(CrawlerTask, task_id)
            assert login_session and login_session.status == "failed"
            assert task and task.status == "cancelled"
        print("worker_verification=ok")
        return 0
    finally:
        for job in jobs:
            try:
                job.delete()
            except Exception:
                pass
        if account_id is not None:
            with SessionLocal() as session:
                session.execute(delete(CrawlerTask).where(CrawlerTask.account_id == account_id))
                session.execute(delete(LoginSession).where(LoginSession.account_id == account_id))
                session.execute(delete(AccountSecret).where(AccountSecret.account_id == account_id))
                session.execute(delete(Account).where(Account.id == account_id))
                session.commit()


if __name__ == "__main__":
    raise SystemExit(main())
