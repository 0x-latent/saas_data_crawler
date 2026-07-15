"""Discover historical crawler artifacts under data/checkpoints."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from saas_crawler.core.paths import CHECKPOINT_DIR, DATA_DIR
from saas_crawler.storage.repositories import get_or_create_asset

from .utils import file_sha256, mtime_datetime


SUPPORTED_SUFFIXES = {".csv", ".json", ".sqlite", ".xlsx", ".xls", ".zip", ".html", ".js"}


def infer_platform(path: Path) -> str:
    text = str(path).replace("\\", "/").lower()
    name = path.name.lower()
    if "magnetic_juxing" in text:
        return "magnetic_juxing"
    if "ks_feigua" in text:
        return "ks_feigua"
    if "xingtu" in text:
        return "xingtu"
    if "feigua" in text:
        return "feigua"
    if "huohua" in text or "phase1_list" in name or "phase2_detail" in name:
        return "huohua"
    if "merged" in name:
        return "merged"
    return "unknown"


def infer_asset_type(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".") or "file"
    text = str(path).replace("\\", "/").lower()
    if "checkpoint" in text or "checkpoints" in text:
        return f"checkpoint_{suffix}"
    if path.name == "magnetic_juxing.sqlite":
        return "sqlite_database"
    if "/mart/" in text:
        return "mart_csv"
    if suffix in {"xlsx", "xls"}:
        return "excel_snapshot"
    if suffix == "json":
        return "raw_json"
    return suffix


def discover_assets(
    session: Session,
    roots: list[Path] | None = None,
    *,
    hash_max_bytes: int = 16 * 1024 * 1024,
) -> list[int]:
    roots = roots or [DATA_DIR, CHECKPOINT_DIR]
    asset_ids: list[int] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            stat = path.stat()
            content_hash = file_sha256(path, max_bytes=hash_max_bytes)
            asset = get_or_create_asset(
                session,
                platform=infer_platform(path),
                asset_type=infer_asset_type(path),
                path=path,
                file_size=stat.st_size,
                file_mtime=mtime_datetime(path),
                content_hash=content_hash,
            )
            session.flush()
            asset_ids.append(asset.id)
    return asset_ids
