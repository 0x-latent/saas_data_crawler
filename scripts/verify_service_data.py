"""Compare imported PostgreSQL rows with registered historical source assets."""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import func, select

from saas_crawler.storage.db import SessionLocal
from saas_crawler.storage.models import (
    DataAsset,
    FeiguaBilibiliSnapshot,
    HuohuaUpSnapshot,
    KsFeiguaBloggerProfile,
    KsFeiguaBloggerTrend,
    KsFeiguaCommerce,
    KsFeiguaRecentLive,
    KsFeiguaRecentVideo,
    KsFeiguaSegment,
    MagneticDimStar,
    MagneticFactStarSource,
    MagneticStarPortrait,
    MagneticStarWork,
)


MAGNETIC_TABLES = {
    "dim_star": MagneticDimStar,
    "fact_star_source": MagneticFactStarSource,
    "star_work": MagneticStarWork,
    "star_portrait": MagneticStarPortrait,
}

KS_TABLES = {
    "mart_blogger_profile.csv": KsFeiguaBloggerProfile,
    "fact_blogger_trend.csv": KsFeiguaBloggerTrend,
    "fact_commerce.csv": KsFeiguaCommerce,
    "fact_recent_lives.csv": KsFeiguaRecentLive,
    "fact_recent_videos.csv": KsFeiguaRecentVideo,
    "fact_segments.csv": KsFeiguaSegment,
}


def _csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return sum(1 for _ in csv.reader(source)) - 1


def main() -> int:
    failures: list[str] = []
    with SessionLocal() as session:
        assets = session.scalars(select(DataAsset)).all()
        print(f"registered_assets={len(assets)}")
        magnetic_asset = next((item for item in assets if item.file_name == "magnetic_juxing.sqlite"), None)
        if magnetic_asset:
            connection = sqlite3.connect(magnetic_asset.file_path)
            try:
                for source_table, model in MAGNETIC_TABLES.items():
                    source_count = connection.execute(f"SELECT COUNT(*) FROM {source_table}").fetchone()[0]
                    target_count = session.scalar(select(func.count()).select_from(model)) or 0
                    print(f"{source_table}: source={source_count} target={target_count}")
                    if source_count != target_count:
                        failures.append(source_table)
            finally:
                connection.close()

        for filename, model in KS_TABLES.items():
            asset = next((item for item in assets if item.file_name == filename and item.platform == "ks_feigua"), None)
            if not asset:
                continue
            source_count = _csv_rows(Path(asset.file_path))
            target_count = session.scalar(select(func.count()).select_from(model)) or 0
            print(f"{filename}: source={source_count} target={target_count}")
            if source_count != target_count:
                failures.append(filename)

        print(f"huohua_snapshots={session.scalar(select(func.count()).select_from(HuohuaUpSnapshot)) or 0}")
        print(f"feigua_snapshots={session.scalar(select(func.count()).select_from(FeiguaBilibiliSnapshot)) or 0}")

    if failures:
        print("mismatches=" + ",".join(failures))
        return 1
    print("verification=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
