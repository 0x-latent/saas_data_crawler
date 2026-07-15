"""SQLAlchemy models for crawler service storage."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


JsonDict = dict[str, Any] | list[Any] | str | int | float | bool | None


class DataAsset(Base):
    __tablename__ = "data_asset"
    __table_args__ = (UniqueConstraint("file_path", name="uq_data_asset_file_path"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(64), index=True)
    asset_type: Mapped[str] = mapped_column(String(64), index=True)
    file_path: Mapped[str] = mapped_column(Text)
    file_name: Mapped[str] = mapped_column(Text)
    file_size: Mapped[int] = mapped_column(BigInteger)
    file_mtime: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    import_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class IngestRun(Base):
    __tablename__ = "ingest_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(64), index=True)
    source_type: Mapped[str] = mapped_column(String(64), index=True)
    source_asset_id: Mapped[int | None] = mapped_column(ForeignKey("data_asset.id"), nullable=True, index=True)
    source_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)
    params_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_asset: Mapped[DataAsset | None] = relationship()


class CrawlerTask(Base):
    __tablename__ = "crawler_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(64), index=True)
    task_type: Mapped[str] = mapped_column(String(64), index=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("account.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    params_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    progress_current: Mapped[int] = mapped_column(Integer, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, default=0)
    log_tail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class RawApiResponse(Base):
    __tablename__ = "raw_api_response"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(64), index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("crawler_task.id"), nullable=True, index=True)
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingest_run.id"), nullable=True, index=True)
    endpoint: Mapped[str] = mapped_column(Text)
    request_payload_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    response_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)


class CreatorIdentity(Base):
    __tablename__ = "creator_identity"
    __table_args__ = (UniqueConstraint("platform", "platform_creator_id", name="uq_creator_identity_platform_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(64), index=True)
    platform_creator_id: Mapped[str] = mapped_column(String(128), index=True)
    canonical_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    core_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    profile_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CreatorSnapshot(Base):
    __tablename__ = "creator_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(64), index=True)
    platform_creator_id: Mapped[str] = mapped_column(String(128), index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("crawler_task.id"), nullable=True, index=True)
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingest_run.id"), nullable=True, index=True)
    nick_name: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    follower_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    province: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    metrics_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    attributes_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    extra_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    items_json: Mapped[JsonDict] = mapped_column(JSONB, default=list)
    source_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Account(Base):
    __tablename__ = "account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(64), index=True)
    display_name: Mapped[str] = mapped_column(Text)
    login_type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="new", index=True)
    username_masked: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone_masked: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cookie_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccountSecret(Base):
    __tablename__ = "account_secret"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), index=True)
    secret_type: Mapped[str] = mapped_column(String(64), index=True)
    encrypted_value: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class LoginSession(Base):
    __tablename__ = "login_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), index=True)
    platform: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    mode: Mapped[str] = mapped_column(String(32))
    qr_image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    latest_screenshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class MagneticDimStar(Base):
    __tablename__ = "magnetic_dim_star"

    star_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    kwai_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fans_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    head_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    profile_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    mcn_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mcn_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_source_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    latest_detail_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)


class MagneticFactStarSource(Base):
    __tablename__ = "magnetic_fact_star_source"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_sqlite_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingest_run.id"), nullable=True, index=True)
    run_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    star_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rank_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    hot_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    star_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    task_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    star_order_tag: Mapped[int | None] = mapped_column(Integer, nullable=True)
    star_order_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    path_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    item_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)


class MagneticStarWork(Base):
    __tablename__ = "magnetic_star_work"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingest_run.id"), nullable=True, index=True)
    star_id: Mapped[str] = mapped_column(String(128), index=True)
    star_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    photo_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    like_cnt: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    view_cnt: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    forward_cnt: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    comment_cnt: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    release_time_millis: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    business: Mapped[int | None] = mapped_column(Integer, nullable=True)
    product_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_industry_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_industry_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)


class MagneticStarPortrait(Base):
    __tablename__ = "magnetic_star_portrait"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_sqlite_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingest_run.id"), nullable=True, index=True)
    star_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    star_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    portrait: Mapped[str | None] = mapped_column(Text, nullable=True)
    group_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    item_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    tgi: Mapped[float | None] = mapped_column(Float, nullable=True)
    item_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)


class KsFeiguaBloggerProfile(Base):
    __tablename__ = "ks_feigua_blogger_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingest_run.id"), nullable=True, index=True)
    blogger_id: Mapped[str] = mapped_column(String(128), index=True)
    nick: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    kwai_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fans: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    row_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    source_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KsFeiguaFactRow(Base):
    __tablename__ = "ks_feigua_fact_row"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingest_run.id"), nullable=True, index=True)
    table_name: Mapped[str] = mapped_column(String(64), index=True)
    blogger_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    row_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    source_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KsFeiguaBloggerTrend(Base):
    __tablename__ = "ks_feigua_blogger_trend"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingest_run.id"), nullable=True, index=True)
    blogger_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    row_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    source_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KsFeiguaCommerce(Base):
    __tablename__ = "ks_feigua_commerce"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingest_run.id"), nullable=True, index=True)
    blogger_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    row_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    source_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KsFeiguaRecentLive(Base):
    __tablename__ = "ks_feigua_recent_live"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingest_run.id"), nullable=True, index=True)
    blogger_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    row_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    source_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KsFeiguaRecentVideo(Base):
    __tablename__ = "ks_feigua_recent_video"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingest_run.id"), nullable=True, index=True)
    blogger_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    row_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    source_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KsFeiguaSegment(Base):
    __tablename__ = "ks_feigua_segment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingest_run.id"), nullable=True, index=True)
    blogger_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    row_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    source_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExcelSnapshot(Base):
    __tablename__ = "excel_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(64), index=True)
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingest_run.id"), nullable=True, index=True)
    platform_creator_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    nick_name: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    row_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    source_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class HuohuaUpSnapshot(Base):
    __tablename__ = "huohua_up_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingest_run.id"), nullable=True, index=True)
    platform_creator_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    nick_name: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    row_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    source_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FeiguaBilibiliSnapshot(Base):
    __tablename__ = "feigua_bilibili_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingest_run.id"), nullable=True, index=True)
    platform_creator_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    nick_name: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    row_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    source_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class XingtuAuthorSnapshot(Base):
    __tablename__ = "xingtu_author_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingest_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingest_run.id"), nullable=True, index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("crawler_task.id"), nullable=True, index=True)
    star_id: Mapped[str] = mapped_column(String(128), index=True)
    core_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    nick_name: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    follower: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    province: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    attributes_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    extra_json: Mapped[JsonDict] = mapped_column(JSONB, default=dict)
    items_json: Mapped[JsonDict] = mapped_column(JSONB, default=list)
    task_infos_json: Mapped[JsonDict] = mapped_column(JSONB, default=list)
    source_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
