"""Repository helpers used by API routes and importers."""

from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (
    Account,
    AccountSecret,
    CrawlerTask,
    CreatorIdentity,
    CreatorSnapshot,
    DataAsset,
    IngestRun,
    LoginSession,
    utcnow,
)


def get_or_create_asset(
    session: Session,
    *,
    platform: str,
    asset_type: str,
    path: Path,
    file_size: int,
    file_mtime: datetime,
    content_hash: str | None = None,
    notes: str | None = None,
) -> DataAsset:
    file_path = str(path.resolve())
    asset = session.scalar(select(DataAsset).where(DataAsset.file_path == file_path))
    if asset:
        changed = (
            asset.file_size != file_size
            or asset.file_mtime != file_mtime
            or (content_hash is not None and asset.content_hash != content_hash)
        )
        asset.platform = platform
        asset.asset_type = asset_type
        asset.file_name = path.name
        asset.file_size = file_size
        asset.file_mtime = file_mtime
        asset.content_hash = content_hash or asset.content_hash
        if changed:
            asset.import_status = "pending"
            asset.imported_at = None
        if notes:
            asset.notes = notes
        return asset
    asset = DataAsset(
        platform=platform,
        asset_type=asset_type,
        file_path=file_path,
        file_name=path.name,
        file_size=file_size,
        file_mtime=file_mtime,
        content_hash=content_hash,
        notes=notes,
    )
    session.add(asset)
    return asset


def start_ingest_run(
    session: Session,
    *,
    platform: str,
    source_type: str,
    source_asset_id: int | None,
    params: dict[str, Any] | None = None,
) -> IngestRun:
    fingerprint = None
    if source_asset_id is not None:
        asset = session.get(DataAsset, source_asset_id)
        if asset:
            fingerprint = asset_fingerprint(asset)
    run = IngestRun(
        platform=platform,
        source_type=source_type,
        source_asset_id=source_asset_id,
        source_fingerprint=fingerprint,
        status="running",
        params_json=params or {},
        started_at=utcnow(),
    )
    session.add(run)
    session.flush()
    return run


def asset_fingerprint(asset: DataAsset) -> str:
    value = "|".join(
        (
            asset.content_hash or "",
            str(asset.file_size),
            asset.file_mtime.isoformat(),
        )
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def get_successful_ingest_run(session: Session, *, asset_id: int, source_type: str) -> IngestRun | None:
    asset = session.get(DataAsset, asset_id)
    if not asset:
        return None
    return session.scalar(
        select(IngestRun)
        .where(
            IngestRun.source_asset_id == asset_id,
            IngestRun.source_type == source_type,
            IngestRun.source_fingerprint == asset_fingerprint(asset),
            IngestRun.status == "success",
        )
        .order_by(IngestRun.id.desc())
        .limit(1)
    )


def finish_ingest_run(
    session: Session,
    run: IngestRun,
    *,
    status: str,
    total_rows: int = 0,
    imported_rows: int = 0,
    error_message: str | None = None,
) -> None:
    run.status = status
    run.total_rows = total_rows
    run.imported_rows = imported_rows
    run.error_message = error_message
    run.finished_at = utcnow()
    if run.source_asset:
        run.source_asset.import_status = "imported" if status == "success" else "failed"
        run.source_asset.imported_at = utcnow() if status == "success" else run.source_asset.imported_at


def upsert_creator_identity(
    session: Session,
    *,
    platform: str,
    platform_creator_id: str,
    canonical_name: str | None = None,
    core_user_id: str | None = None,
    profile_url: str | None = None,
    avatar_url: str | None = None,
) -> CreatorIdentity:
    creator_id = str(platform_creator_id)
    cache = session.info.setdefault("creator_identity_cache", {})
    cache_key = (platform, creator_id)
    identity = cache.get(cache_key)
    if identity is None:
        identity = session.scalar(
            select(CreatorIdentity).where(
                CreatorIdentity.platform == platform,
                CreatorIdentity.platform_creator_id == creator_id,
            )
        )
    if not identity:
        identity = CreatorIdentity(platform=platform, platform_creator_id=creator_id)
        session.add(identity)
    cache[cache_key] = identity
    if canonical_name:
        identity.canonical_name = canonical_name
    if core_user_id:
        identity.core_user_id = str(core_user_id)
    if profile_url:
        identity.profile_url = profile_url
    if avatar_url:
        identity.avatar_url = avatar_url
    identity.updated_at = utcnow()
    return identity


def create_creator_snapshot(
    session: Session,
    *,
    platform: str,
    platform_creator_id: str,
    ingest_run_id: int | None = None,
    task_id: int | None = None,
    nick_name: str | None = None,
    follower_count: int | None = None,
    province: str | None = None,
    city: str | None = None,
    gender: str | None = None,
    metrics_json: Any = None,
    attributes_json: Any = None,
    extra_json: Any = None,
    items_json: Any = None,
    source_file: str | None = None,
    captured_at: datetime | None = None,
) -> CreatorSnapshot:
    snapshot = CreatorSnapshot(
        platform=platform,
        platform_creator_id=str(platform_creator_id),
        ingest_run_id=ingest_run_id,
        task_id=task_id,
        nick_name=nick_name,
        follower_count=follower_count,
        province=province,
        city=city,
        gender=gender,
        metrics_json=metrics_json or {},
        attributes_json=attributes_json or {},
        extra_json=extra_json or {},
        items_json=items_json or [],
        source_file=source_file,
        captured_at=captured_at,
    )
    session.add(snapshot)
    return snapshot


def create_task(session: Session, *, platform: str, task_type: str, params: dict[str, Any], account_id: int | None = None) -> CrawlerTask:
    task = CrawlerTask(platform=platform, task_type=task_type, params_json=params, account_id=account_id, status="pending")
    session.add(task)
    session.flush()
    return task


def update_task_status(
    session: Session,
    task: CrawlerTask,
    *,
    status: str,
    progress_current: int | None = None,
    progress_total: int | None = None,
    log_tail: str | None = None,
    error_message: str | None = None,
) -> None:
    task.status = status
    if status == "running" and task.started_at is None:
        task.started_at = utcnow()
    if status in {"success", "failed", "cancelled"}:
        task.finished_at = utcnow()
    if progress_current is not None:
        task.progress_current = progress_current
    if progress_total is not None:
        task.progress_total = progress_total
    if log_tail is not None:
        task.log_tail = log_tail[-4000:]
    if error_message is not None:
        task.error_message = error_message


def create_account(
    session: Session,
    *,
    platform: str,
    display_name: str,
    login_type: str,
    username_masked: str | None = None,
    phone_masked: str | None = None,
) -> Account:
    account = Account(
        platform=platform,
        display_name=display_name,
        login_type=login_type,
        username_masked=username_masked,
        phone_masked=phone_masked,
        status="new",
    )
    session.add(account)
    session.flush()
    return account


def set_account_secret(session: Session, *, account_id: int, secret_type: str, encrypted_value: str) -> AccountSecret:
    secret = session.scalar(
        select(AccountSecret).where(AccountSecret.account_id == account_id, AccountSecret.secret_type == secret_type)
    )
    if not secret:
        secret = AccountSecret(account_id=account_id, secret_type=secret_type, version=1, encrypted_value=encrypted_value)
        session.add(secret)
    else:
        secret.encrypted_value = encrypted_value
        secret.version += 1
        secret.updated_at = utcnow()
    return secret


def create_login_session(session: Session, *, account: Account, mode: str, prompt_message: str | None = None) -> LoginSession:
    login_session = LoginSession(
        account_id=account.id,
        platform=account.platform,
        mode=mode,
        status="pending",
        prompt_message=prompt_message,
    )
    session.add(login_session)
    session.flush()
    return login_session


def dashboard_counts(session: Session) -> dict[str, Any]:
    platforms = session.execute(
        select(CreatorSnapshot.platform, func.count()).group_by(CreatorSnapshot.platform)
    ).all()
    tasks = session.scalar(select(func.count()).select_from(CrawlerTask)) or 0
    assets = session.scalar(select(func.count()).select_from(DataAsset)) or 0
    accounts = session.scalar(select(func.count()).select_from(Account)) or 0
    return {
        "creators_by_platform": {platform: count for platform, count in platforms},
        "tasks": tasks,
        "assets": assets,
        "accounts": accounts,
    }
