"""Import Feigua Kuaishou dashboard mart CSV files."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from saas_crawler.storage.models import (
    KsFeiguaBloggerProfile,
    KsFeiguaBloggerTrend,
    KsFeiguaCommerce,
    KsFeiguaFactRow,
    KsFeiguaRecentLive,
    KsFeiguaRecentVideo,
    KsFeiguaSegment,
)
from saas_crawler.storage.repositories import (
    create_creator_snapshot,
    finish_ingest_run,
    get_successful_ingest_run,
    start_ingest_run,
    upsert_creator_identity,
)

from .utils import as_float, as_int, read_csv_rows


MART_FILES = {
    "mart_blogger_profile.csv": "profile",
    "fact_blogger_trend.csv": "trend",
    "fact_commerce.csv": "commerce",
    "fact_recent_lives.csv": "recent_live",
    "fact_recent_videos.csv": "recent_video",
    "fact_segments.csv": "segment",
    "quality_report.csv": "quality",
}

FACT_MODELS = {
    "trend": KsFeiguaBloggerTrend,
    "commerce": KsFeiguaCommerce,
    "recent_live": KsFeiguaRecentLive,
    "recent_video": KsFeiguaRecentVideo,
    "segment": KsFeiguaSegment,
}


def import_ks_feigua_mart(session: Session, asset_id: int, path: Path) -> int:
    if path.is_file():
        if path.name not in MART_FILES:
            raise ValueError(f"Unsupported Feigua mart file: {path.name}")
        input_files = [(path, MART_FILES[path.name])]
    else:
        input_files = [
            (path / filename, table_name)
            for filename, table_name in MART_FILES.items()
            if (path / filename).exists()
        ]
    source_type = f"mart_{input_files[0][1]}" if len(input_files) == 1 else "mart_directory"
    existing = get_successful_ingest_run(session, asset_id=asset_id, source_type=source_type)
    if existing:
        return existing.imported_rows
    run = start_ingest_run(
        session,
        platform="ks_feigua",
        source_type=source_type,
        source_asset_id=asset_id,
        params={"files": [str(csv_path) for csv_path, _ in input_files]},
    )
    try:
        imported = 0
        for csv_path, table_name in input_files:
            rows = read_csv_rows(csv_path)
            if table_name == "profile":
                for row in rows:
                    blogger_id = str(row.get("blogger_id") or "").strip()
                    if not blogger_id:
                        continue
                    upsert_creator_identity(
                        session,
                        platform="ks_feigua",
                        platform_creator_id=blogger_id,
                        canonical_name=row.get("nick"),
                        core_user_id=row.get("kwaiId"),
                        profile_url=row.get("jumpUrl"),
                    )
                    session.add(KsFeiguaBloggerProfile(
                        ingest_run_id=run.id,
                        blogger_id=blogger_id,
                        nick=row.get("nick"),
                        kwai_id=row.get("kwaiId"),
                        fans=as_int(row.get("fans")),
                        score=as_float(row.get("score")),
                        row_json=row,
                        source_file=str(csv_path),
                    ))
                    create_creator_snapshot(
                        session,
                        platform="ks_feigua",
                        platform_creator_id=blogger_id,
                        ingest_run_id=run.id,
                        nick_name=row.get("nick"),
                        follower_count=as_int(row.get("fans")),
                        metrics_json=row,
                        attributes_json=row,
                        source_file=str(csv_path),
                    )
                    imported += 1
            else:
                model = FACT_MODELS.get(table_name)
                for row in rows:
                    values = {
                        "ingest_run_id": run.id,
                        "blogger_id": str(row.get("blogger_id") or "") or None,
                        "row_json": row,
                        "source_file": str(csv_path),
                    }
                    if model:
                        session.add(model(**values))
                    else:
                        session.add(KsFeiguaFactRow(table_name=table_name, **values))
                    imported += 1
        finish_ingest_run(session, run, status="success", total_rows=imported, imported_rows=imported)
        session.commit()
        return imported
    except Exception as exc:
        session.rollback()
        run = session.merge(run)
        finish_ingest_run(session, run, status="failed", error_message=str(exc))
        session.commit()
        raise
