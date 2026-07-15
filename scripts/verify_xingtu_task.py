"""Verify one Xingtu task writes raw responses and creator snapshots."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import delete, func, select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from saas_crawler.accounts.secrets import encrypt_secret  # noqa: E402
from saas_crawler.storage import settings  # noqa: E402
from saas_crawler.storage.db import SessionLocal  # noqa: E402
from saas_crawler.storage.models import (  # noqa: E402
    Account,
    AccountSecret,
    CrawlerTask,
    CreatorIdentity,
    CreatorSnapshot,
    RawApiResponse,
    XingtuAuthorSnapshot,
)
from saas_crawler.storage.repositories import create_account, create_task, set_account_secret  # noqa: E402
from saas_crawler.tasks import task_runner  # noqa: E402


VALIDATION_STAR_ID = "__xingtu_task_validation__"


async def _captured_response(_cookie: str, _args):
    return {
        "requests": [{"post_data": {"page_param": {"page": "1", "limit": "20"}}, "headers": {}}],
        "responses": [{
            "body": {
                "base_resp": {"status_code": 0},
                "pagination": {"limit": 20, "total_count": 1},
                "authors": [{
                    "star_id": VALIDATION_STAR_ID,
                    "attribute_datas": {"id": VALIDATION_STAR_ID, "nick_name": "任务验证达人", "follower": 1234},
                    "extra_data": {},
                    "items": [],
                    "task_infos": [],
                }],
            }
        }],
    }


def main() -> int:
    original_key = settings.CRAWLER_SECRET_KEY
    original_capture = task_runner.xingtu_scraper.capture_author_square
    settings.CRAWLER_SECRET_KEY = "xingtu-task-validation-key"
    account_id: int | None = None
    task_id: int | None = None
    try:
        with SessionLocal() as session:
            account = create_account(
                session,
                platform="xingtu",
                display_name="__xingtu_task_validation__",
                login_type="qr",
            )
            account_id = account.id
            set_account_secret(
                session,
                account_id=account.id,
                secret_type="cookie",
                encrypted_value=encrypt_secret("sessionid=validation"),
            )
            task = create_task(
                session,
                platform="xingtu",
                task_type="author_square",
                account_id=account.id,
                params={"max_pages": 1},
            )
            task_id = task.id
            session.commit()

        task_runner.xingtu_scraper.capture_author_square = _captured_response
        task_runner.run_task(task_id)
        with SessionLocal() as session:
            task = session.get(CrawlerTask, task_id)
            raw_count = session.scalar(select(func.count()).select_from(RawApiResponse).where(RawApiResponse.task_id == task_id))
            snapshot_count = session.scalar(
                select(func.count()).select_from(XingtuAuthorSnapshot).where(XingtuAuthorSnapshot.task_id == task_id)
            )
            assert task and task.status == "success" and task.progress_current == 1
            assert raw_count == 1 and snapshot_count == 1
        print("xingtu_task_verification=ok")
        return 0
    finally:
        task_runner.xingtu_scraper.capture_author_square = original_capture
        settings.CRAWLER_SECRET_KEY = original_key
        if account_id is not None:
            with SessionLocal() as session:
                if task_id is not None:
                    session.execute(delete(XingtuAuthorSnapshot).where(XingtuAuthorSnapshot.task_id == task_id))
                    session.execute(delete(CreatorSnapshot).where(CreatorSnapshot.task_id == task_id))
                    session.execute(delete(RawApiResponse).where(RawApiResponse.task_id == task_id))
                    session.execute(delete(CrawlerTask).where(CrawlerTask.id == task_id))
                session.execute(
                    delete(CreatorIdentity).where(
                        CreatorIdentity.platform == "xingtu",
                        CreatorIdentity.platform_creator_id == VALIDATION_STAR_ID,
                    )
                )
                session.execute(delete(AccountSecret).where(AccountSecret.account_id == account_id))
                session.execute(delete(Account).where(Account.id == account_id))
                session.commit()


if __name__ == "__main__":
    raise SystemExit(main())
