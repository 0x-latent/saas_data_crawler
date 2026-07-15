"""Creator search/detail routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from saas_crawler.storage.db import get_session
from saas_crawler.storage.models import CreatorSnapshot

from .serializers import model_to_dict


router = APIRouter(tags=["creators"])


@router.get("/creators")
def list_creators(
    platform: str | None = None,
    q: str | None = None,
    min_followers: int | None = None,
    province: str | None = None,
    city: str | None = None,
    source: str | None = None,
    limit: int = Query(default=50, le=200),
    session: Session = Depends(get_session),
):
    filters = []
    if platform:
        filters.append(CreatorSnapshot.platform == platform)
    if q:
        filters.append(CreatorSnapshot.nick_name.ilike(f"%{q}%"))
    if min_followers is not None:
        filters.append(CreatorSnapshot.follower_count >= min_followers)
    if province:
        filters.append(CreatorSnapshot.province.ilike(f"%{province}%"))
    if city:
        filters.append(CreatorSnapshot.city.ilike(f"%{city}%"))
    if source:
        filters.append(CreatorSnapshot.source_file.ilike(f"%{source}%"))
    ranked = (
        select(
            CreatorSnapshot.id.label("snapshot_id"),
            func.row_number()
            .over(
                partition_by=(CreatorSnapshot.platform, CreatorSnapshot.platform_creator_id),
                order_by=(CreatorSnapshot.imported_at.desc(), CreatorSnapshot.id.desc()),
            )
            .label("row_number"),
        )
        .where(*filters)
        .subquery()
    )
    stmt = (
        select(CreatorSnapshot)
        .join(ranked, CreatorSnapshot.id == ranked.c.snapshot_id)
        .where(ranked.c.row_number == 1)
        .order_by(desc(CreatorSnapshot.imported_at))
        .limit(limit)
    )
    return [model_to_dict(row) for row in session.scalars(stmt).all()]


@router.get("/creators/{platform}/{platform_creator_id}")
def get_creator(platform: str, platform_creator_id: str, session: Session = Depends(get_session)):
    row = session.scalars(
        select(CreatorSnapshot)
        .where(CreatorSnapshot.platform == platform, CreatorSnapshot.platform_creator_id == platform_creator_id)
        .order_by(desc(CreatorSnapshot.imported_at))
        .limit(1)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="creator not found")
    return model_to_dict(row)
