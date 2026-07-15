"""Import the existing Magnetic Juxing SQLite database into PostgreSQL."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import insert
from sqlalchemy.orm import Session

from saas_crawler.storage.models import (
    MagneticDimStar,
    MagneticFactStarSource,
    MagneticStarPortrait,
    MagneticStarWork,
    RawApiResponse,
)
from saas_crawler.storage.repositories import (
    create_creator_snapshot,
    finish_ingest_run,
    get_successful_ingest_run,
    start_ingest_run,
    upsert_creator_identity,
)

from .utils import as_float, as_int, json_loads_maybe, parse_dt


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _rows(conn: sqlite3.Connection, table: str, batch_size: int = 5000) -> Iterable[list[sqlite3.Row]]:
    offset = 0
    while True:
        batch = conn.execute(f"SELECT * FROM {table} LIMIT ? OFFSET ?", (batch_size, offset)).fetchall()
        if not batch:
            break
        yield batch
        offset += batch_size


def _json(value: Any, default: Any = None) -> Any:
    return json_loads_maybe(value, default if default is not None else {})


def _run_map(conn: sqlite3.Connection, session: Session, asset_id: int) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for row in conn.execute("SELECT * FROM runs").fetchall():
        run = start_ingest_run(
            session,
            platform="magnetic_juxing",
            source_type=str(row["action"] or "sqlite_run"),
            source_asset_id=asset_id,
            params=_json(row["params_json"], {}),
        )
        run.started_at = parse_dt(row["started_at"]) or run.started_at
        run.finished_at = parse_dt(row["finished_at"])
        run.status = row["status"] or "unknown"
        mapping[row["run_id"]] = run.id
    session.flush()
    return mapping


def import_magnetic_sqlite(session: Session, asset_id: int, path: Path, *, batch_size: int = 5000) -> int:
    existing = get_successful_ingest_run(session, asset_id=asset_id, source_type="sqlite_database")
    if existing:
        return existing.imported_rows
    conn = _connect(path)
    top_run = start_ingest_run(
        session,
        platform="magnetic_juxing",
        source_type="sqlite_database",
        source_asset_id=asset_id,
        params={"path": str(path)},
    )
    imported = 0
    try:
        run_map = _run_map(conn, session, asset_id)

        for batch in _rows(conn, "dim_star", batch_size):
            for row in batch:
                latest_source = _json(row["latest_source_json"], {})
                latest_detail = _json(row["latest_detail_json"], {})
                star_id = str(row["star_id"])
                session.merge(MagneticDimStar(
                    star_id=star_id,
                    user_id=row["user_id"],
                    kwai_id=row["kwai_id"],
                    name=row["name"],
                    gender=row["gender"],
                    fans_number=as_int(row["fans_number"]),
                    head_url=row["head_url"],
                    profile_id=row["profile_id"],
                    profile_url=row["profile_url"],
                    mcn_id=row["mcn_id"],
                    mcn_name=row["mcn_name"],
                    updated_at=parse_dt(row["updated_at"]),
                    latest_source_json=latest_source,
                    latest_detail_json=latest_detail,
                ))
                upsert_creator_identity(
                    session,
                    platform="magnetic_juxing",
                    platform_creator_id=star_id,
                    canonical_name=row["name"],
                    core_user_id=row["user_id"],
                    profile_url=row["profile_url"],
                    avatar_url=row["head_url"],
                )
                create_creator_snapshot(
                    session,
                    platform="magnetic_juxing",
                    platform_creator_id=star_id,
                    ingest_run_id=top_run.id,
                    nick_name=row["name"],
                    follower_count=as_int(row["fans_number"]),
                    gender=row["gender"],
                    attributes_json=latest_source,
                    extra_json=latest_detail,
                    source_file=str(path),
                    captured_at=parse_dt(row["updated_at"]),
                )
                imported += 1
            session.flush()

        for table, handler in (
            ("raw_api_response", _import_raw_response),
            ("fact_star_source", _import_fact_source),
            ("star_work", _import_star_work),
            ("star_portrait", _import_star_portrait),
        ):
            for batch in _rows(conn, table, batch_size):
                handler(session, batch, run_map, top_run.id)
                imported += len(batch)
                session.flush()

        finish_ingest_run(session, top_run, status="success", total_rows=imported, imported_rows=imported)
        session.commit()
        return imported
    except Exception as exc:
        session.rollback()
        top_run = session.merge(top_run)
        finish_ingest_run(session, top_run, status="failed", total_rows=imported, imported_rows=imported, error_message=str(exc))
        session.commit()
        raise
    finally:
        conn.close()


def _import_raw_response(session: Session, batch: list[sqlite3.Row], run_map: dict[str, int], fallback_run_id: int) -> None:
    values = [
        {
            "platform": "magnetic_juxing",
            "ingest_run_id": run_map.get(row["run_id"], fallback_run_id),
            "endpoint": row["endpoint"],
            "request_payload_json": _json(row["payload_json"], {}),
            "response_json": _json(row["response_json"], {}),
            "fetched_at": parse_dt(row["fetched_at"]),
            "status_code": None,
        }
        for row in batch
    ]
    session.execute(insert(RawApiResponse), values)


def _import_fact_source(session: Session, batch: list[sqlite3.Row], run_map: dict[str, int], fallback_run_id: int) -> None:
    values = [
        {
            "source_sqlite_id": row["id"],
            "ingest_run_id": run_map.get(row["run_id"], fallback_run_id),
            "run_id": row["run_id"],
            "star_id": row["star_id"],
            "source_type": row["source_type"],
            "endpoint": row["endpoint"],
            "account_id": row["account_id"],
            "fetched_at": parse_dt(row["fetched_at"]),
            "page": as_int(row["page"]),
            "rank": as_int(row["rank"]),
            "rank_key": row["rank_key"],
            "rank_name": row["rank_name"],
            "hot_id": as_int(row["hot_id"]),
            "star_type": as_int(row["star_type"]),
            "task_type": as_int(row["task_type"]),
            "star_order_tag": as_int(row["star_order_tag"]),
            "star_order_type": as_int(row["star_order_type"]),
            "path_source": row["path_source"],
            "payload_json": _json(row["payload_json"], {}),
            "item_json": _json(row["item_json"], {}),
        }
        for row in batch
    ]
    session.execute(insert(MagneticFactStarSource), values)


def _import_star_work(session: Session, batch: list[sqlite3.Row], run_map: dict[str, int], fallback_run_id: int) -> None:
    values = [
        {
            "ingest_run_id": fallback_run_id,
            "star_id": row["star_id"],
            "star_type": as_int(row["star_type"]),
            "photo_id": row["photo_id"],
            "fetched_at": parse_dt(row["fetched_at"]),
            "caption": row["caption"],
            "like_cnt": as_int(row["like_cnt"]),
            "view_cnt": as_int(row["view_cnt"]),
            "forward_cnt": as_int(row["forward_cnt"]),
            "comment_cnt": as_int(row["comment_cnt"]),
            "release_time_millis": as_int(row["release_time_millis"]),
            "business": as_int(row["business"]),
            "product_name": row["product_name"],
            "first_industry_id": as_int(row["first_industry_id"]),
            "first_industry_name": row["first_industry_name"],
            "data_json": _json(row["data_json"], {}),
        }
        for row in batch
    ]
    session.execute(insert(MagneticStarWork), values)


def _import_star_portrait(session: Session, batch: list[sqlite3.Row], run_map: dict[str, int], fallback_run_id: int) -> None:
    values = [
        {
            "source_sqlite_id": row["id"],
            "ingest_run_id": fallback_run_id,
            "star_id": row["star_id"],
            "star_type": as_int(row["star_type"]),
            "fetched_at": parse_dt(row["fetched_at"]),
            "portrait": row["portrait"],
            "group_name": row["group_name"],
            "item_index": as_int(row["item_index"]),
            "label": row["label"],
            "value": as_float(row["value"]),
            "tgi": as_float(row["tgi"]),
            "item_json": _json(row["item_json"], {}),
        }
        for row in batch
    ]
    session.execute(insert(MagneticStarPortrait), values)
