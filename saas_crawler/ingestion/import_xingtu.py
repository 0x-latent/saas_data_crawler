"""Import Xingtu author square JSON/CSV exports."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from saas_crawler.storage.models import CreatorSnapshot, XingtuAuthorSnapshot
from saas_crawler.storage.repositories import (
    create_creator_snapshot,
    finish_ingest_run,
    get_successful_ingest_run,
    start_ingest_run,
    upsert_creator_identity,
)

from .utils import as_int, json_loads_maybe, parse_dt


def _authors_from_json(path: Path) -> tuple[list[dict[str, Any]], str | None]:
    data = json.loads(path.read_text(encoding="utf-8"))
    authors = data.get("authors") or []
    captured_at = data.get("captured_at")
    return authors, captured_at


def _authors_from_csv(path: Path) -> tuple[list[dict[str, Any]], str | None]:
    authors: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            attr = {
                key: value
                for key, value in row.items()
                if key not in {"star_id", "_task_infos", "_items", "_extra_data"}
            }
            authors.append({
                "star_id": row.get("star_id"),
                "attribute_datas": attr,
                "extra_data": json_loads_maybe(row.get("_extra_data"), {}),
                "items": json_loads_maybe(row.get("_items"), []),
                "task_infos": json_loads_maybe(row.get("_task_infos"), []),
            })
    return authors, None


def import_xingtu_asset(session: Session, asset_id: int, path: Path) -> int:
    source_type = path.suffix.lower().lstrip(".")
    existing = get_successful_ingest_run(session, asset_id=asset_id, source_type=source_type)
    if existing:
        return existing.imported_rows
    run = start_ingest_run(
        session,
        platform="xingtu",
        source_type=source_type,
        source_asset_id=asset_id,
        params={"path": str(path)},
    )
    try:
        if path.suffix.lower() == ".json":
            authors, captured_at_text = _authors_from_json(path)
        else:
            authors, captured_at_text = _authors_from_csv(path)
        captured_at = parse_dt(captured_at_text) if captured_at_text else None
        imported = 0
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
                ingest_run_id=run.id,
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
                source_file=str(path),
                captured_at=captured_at,
            ))
            create_creator_snapshot(
                session,
                platform="xingtu",
                platform_creator_id=star_id,
                ingest_run_id=run.id,
                nick_name=nick,
                follower_count=as_int(attrs.get("follower")),
                province=attrs.get("province"),
                city=attrs.get("city"),
                gender=str(attrs.get("gender")) if attrs.get("gender") is not None else None,
                attributes_json=attrs,
                extra_json=author.get("extra_data") or {},
                items_json=author.get("items") or [],
                source_file=str(path),
                captured_at=captured_at,
            )
            imported += 1
        finish_ingest_run(session, run, status="success", total_rows=len(authors), imported_rows=imported)
        session.commit()
        return imported
    except Exception as exc:
        session.rollback()
        run = session.merge(run)
        finish_ingest_run(session, run, status="failed", error_message=str(exc))
        session.commit()
        raise
