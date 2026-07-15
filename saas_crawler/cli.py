"""Project CLI for platform discovery and service operations."""

from __future__ import annotations

import argparse
from pathlib import Path

from .platforms.registry import list_platforms


def main() -> int:
    parser = argparse.ArgumentParser(prog="saas-crawler")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("platforms", help="List registered crawler platforms")
    subparsers.add_parser("db-init", help="Create database tables without Alembic")
    subparsers.add_parser("discover-assets", help="Scan data/checkpoints and register assets")
    ingest_parser = subparsers.add_parser("ingest-asset", help="Import one registered asset")
    ingest_parser.add_argument("asset_id", type=int)
    api_parser = subparsers.add_parser("api", help="Start FastAPI dev server")
    api_parser.add_argument("--host", default="0.0.0.0")
    api_parser.add_argument("--port", type=int, default=8000)
    api_parser.add_argument("--reload", action="store_true")
    subparsers.add_parser("worker", help="Start RQ worker")
    subparsers.add_parser("login-worker", help="Start login RQ worker")

    args = parser.parse_args()
    if args.command == "platforms":
        for platform in list_platforms():
            print(f"{platform.key}\t{platform.name}\t{platform.script}\t{platform.description}")
        return 0

    if args.command == "db-init":
        from .storage.db import init_database

        init_database()
        print("Database tables created.")
        return 0

    if args.command == "discover-assets":
        from .ingestion.discover_assets import discover_assets
        from .storage.db import SessionLocal

        with SessionLocal() as session:
            ids = discover_assets(session)
            session.commit()
        print(f"Discovered {len(ids)} assets.")
        return 0

    if args.command == "ingest-asset":
        from .ingestion.import_excel_sources import import_excel_asset
        from .ingestion.import_ks_feigua import import_ks_feigua_mart
        from .ingestion.import_magnetic import import_magnetic_sqlite
        from .ingestion.import_xingtu import import_xingtu_asset
        from .storage.db import SessionLocal
        from .storage.models import DataAsset

        with SessionLocal() as session:
            asset = session.get(DataAsset, args.asset_id)
            if not asset:
                raise SystemExit(f"Asset not found: {args.asset_id}")
            path = Path(asset.file_path)
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
                count = 0
        print(f"Imported rows: {count}")
        return 0

    if args.command == "api":
        import uvicorn

        uvicorn.run("saas_crawler.api.main:app", host=args.host, port=args.port, reload=args.reload)
        return 0

    if args.command == "worker":
        from .tasks.worker import main as worker_main

        worker_main()
        return 0

    if args.command == "login-worker":
        from .accounts.worker import main as login_worker_main

        login_worker_main()
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
