"""Asset discovery and ingestion routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from saas_crawler.ingestion.discover_assets import discover_assets
from saas_crawler.ingestion.import_excel_sources import import_excel_asset
from saas_crawler.ingestion.import_ks_feigua import import_ks_feigua_mart
from saas_crawler.ingestion.import_magnetic import import_magnetic_sqlite
from saas_crawler.ingestion.import_xingtu import import_xingtu_asset
from saas_crawler.storage.db import get_session
from saas_crawler.storage.models import DataAsset, IngestRun

from .serializers import model_to_dict


router = APIRouter(tags=["assets"])


@router.get("/assets")
def list_assets(platform: str | None = None, status: str | None = None, session: Session = Depends(get_session)):
    stmt = select(DataAsset).order_by(desc(DataAsset.discovered_at))
    if platform:
        stmt = stmt.where(DataAsset.platform == platform)
    if status:
        stmt = stmt.where(DataAsset.import_status == status)
    return [model_to_dict(asset) for asset in session.scalars(stmt).all()]


@router.post("/assets/discover")
def discover(session: Session = Depends(get_session)):
    ids = discover_assets(session)
    session.commit()
    return {"count": len(ids), "asset_ids": ids}


@router.post("/ingest/{asset_id}")
def ingest(asset_id: int, session: Session = Depends(get_session)):
    asset = session.get(DataAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="asset not found")
    path = Path(asset.file_path)
    if not path.exists():
        raise HTTPException(status_code=400, detail="asset file does not exist")
    if asset.platform == "magnetic_juxing" and asset.asset_type == "sqlite_database":
        count = import_magnetic_sqlite(session, asset.id, path)
    elif asset.platform == "ks_feigua" and asset.asset_type == "mart_csv":
        count = import_ks_feigua_mart(session, asset.id, path)
    elif asset.platform in {"huohua", "feigua", "merged"} and asset.asset_type == "excel_snapshot":
        count = import_excel_asset(session, asset.id, path)
    elif asset.platform == "xingtu" and path.suffix.lower() in {".json", ".csv"}:
        count = import_xingtu_asset(session, asset.id, path)
    else:
        asset.import_status = "registered_only"
        session.commit()
        return {"asset_id": asset.id, "status": "registered_only", "message": "No structural importer for this asset."}
    return {"asset_id": asset.id, "status": "imported", "imported_rows": count}


@router.get("/ingest-runs")
def list_ingest_runs(session: Session = Depends(get_session)):
    runs = session.scalars(select(IngestRun).order_by(desc(IngestRun.started_at)).limit(200)).all()
    return [model_to_dict(run) for run in runs]
