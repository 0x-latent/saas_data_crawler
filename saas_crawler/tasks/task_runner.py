"""Background task execution."""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import time
from typing import Any

import requests
from sqlalchemy import select

from saas_crawler.accounts.secrets import decrypt_secret
from saas_crawler.storage.db import SessionLocal
from saas_crawler.storage.models import AccountSecret, CrawlerTask, RawApiResponse, XingtuAuthorSnapshot
from saas_crawler.storage.repositories import (
    create_creator_snapshot,
    update_task_status,
    upsert_creator_identity,
)
from saas_crawler.ingestion.utils import as_int

from scripts import xingtu_scraper


def run_task(task_id: int) -> None:
    with SessionLocal() as session:
        task = session.get(CrawlerTask, task_id)
        if not task:
            return
        if task.status == "cancelled":
            return
        update_task_status(session, task, status="running", log_tail="Task started.")
        session.commit()
        try:
            if task.platform == "xingtu" and task.task_type == "author_square":
                asyncio.run(_run_xingtu_author_square(session, task))
            else:
                raise ValueError(f"Unsupported task {task.platform}/{task.task_type}")
            session.refresh(task)
            if task.status == "cancelled":
                return
            update_task_status(session, task, status="success", log_tail=f"{task.log_tail}\nTask finished.")
            session.commit()
        except Exception as exc:
            session.rollback()
            task = session.get(CrawlerTask, task_id)
            if task:
                update_task_status(session, task, status="failed", error_message=str(exc), log_tail=f"{task.log_tail}\n{exc}")
                session.commit()
            raise


async def _run_xingtu_author_square(session, task: CrawlerTask) -> None:
    params = task.params_json or {}
    cookie = _cookie_for_task(session, task)
    args = argparse.Namespace(
        cdp_url=params.get("cdp_url"),
        browser_channel=params.get("browser_channel", "chrome"),
        headful=bool(params.get("headful", False)),
        timeout_ms=int(params.get("timeout_ms", 45_000)),
    )
    captured = await xingtu_scraper.capture_author_square(cookie, args)
    if not captured["requests"]:
        raise RuntimeError("No Xingtu author square request captured.")
    seed_payload = captured["requests"][0]["post_data"]
    if not isinstance(seed_payload, dict):
        raise RuntimeError("Captured Xingtu request body is not JSON.")
    seed_body = captured["responses"][0]["body"] if captured["responses"] else {}
    headers = xingtu_scraper.replay_headers(captured["requests"][0], cookie)
    pagination = seed_body.get("pagination") if isinstance(seed_body, dict) else {}
    page_size = int(params.get("page_size") or (pagination or {}).get("limit") or 20)
    max_pages = int(params.get("max_pages") or 1)
    delay = float(params.get("delay", xingtu_scraper.REQUEST_DELAY))
    total_count = int((pagination or {}).get("total_count") or 0)
    total_pages = (total_count + page_size - 1) // page_size if total_count else max_pages
    max_pages = min(max_pages, total_pages) if max_pages else total_pages
    update_task_status(session, task, status="running", progress_current=0, progress_total=max_pages)
    session.commit()

    req_session = requests.Session()
    for page_num in range(1, max_pages + 1):
        task = session.get(CrawlerTask, task.id)
        if task.status == "cancelled":
            return
        payload = copy.deepcopy(seed_payload)
        payload.setdefault("page_param", {})
        payload["page_param"]["page"] = str(page_num)
        payload["page_param"]["limit"] = str(page_size)
        if page_num == 1 and isinstance(seed_body, dict) and int((pagination or {}).get("limit") or 0) == page_size:
            body = seed_body
        else:
            body = xingtu_scraper.post_author_square(req_session, headers, payload)
            time.sleep(delay)
        session.add(RawApiResponse(
            platform="xingtu",
            task_id=task.id,
            endpoint=xingtu_scraper.AUTHOR_SQUARE_API,
            request_payload_json=payload,
            response_json=body,
            page=page_num,
            status_code=(body.get("base_resp") or {}).get("status_code"),
        ))
        _store_xingtu_authors(session, task.id, body.get("authors") or [])
        update_task_status(
            session,
            task,
            status="running",
            progress_current=page_num,
            progress_total=max_pages,
            log_tail=f"Imported page {page_num}/{max_pages}",
        )
        session.commit()


def _cookie_for_task(session, task: CrawlerTask) -> str:
    if task.account_id:
        secret = session.scalar(
            select(AccountSecret).where(AccountSecret.account_id == task.account_id, AccountSecret.secret_type == "cookie")
        )
        if secret:
            return decrypt_secret(secret.encrypted_value)
    raise RuntimeError("Xingtu task requires an account with an encrypted cookie secret.")


def _store_xingtu_authors(session, task_id: int, authors: list[dict[str, Any]]) -> None:
    for author in authors:
        attrs = author.get("attribute_datas") or {}
        star_id = str(author.get("star_id") or attrs.get("id") or "").strip()
        if not star_id:
            continue
        nick = attrs.get("nick_name")
        upsert_creator_identity(
            session,
            platform="xingtu",
            platform_creator_id=star_id,
            canonical_name=nick,
            core_user_id=attrs.get("core_user_id"),
            avatar_url=attrs.get("avatar_uri"),
        )
        session.add(XingtuAuthorSnapshot(
            task_id=task_id,
            star_id=star_id,
            core_user_id=attrs.get("core_user_id"),
            nick_name=nick,
            follower=as_int(attrs.get("follower")),
            province=attrs.get("province"),
            city=attrs.get("city"),
            gender=str(attrs.get("gender")) if attrs.get("gender") is not None else None,
            attributes_json=attrs,
            extra_json=author.get("extra_data") or {},
            items_json=author.get("items") or [],
            task_infos_json=author.get("task_infos") or [],
        ))
        create_creator_snapshot(
            session,
            platform="xingtu",
            platform_creator_id=star_id,
            task_id=task_id,
            nick_name=nick,
            follower_count=as_int(attrs.get("follower")),
            province=attrs.get("province"),
            city=attrs.get("city"),
            gender=str(attrs.get("gender")) if attrs.get("gender") is not None else None,
            attributes_json=attrs,
            extra_json=author.get("extra_data") or {},
            items_json=author.get("items") or [],
        )
