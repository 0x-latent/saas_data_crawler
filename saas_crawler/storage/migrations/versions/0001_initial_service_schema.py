"""initial service schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-10
"""

from alembic import op

from saas_crawler.storage.models import Base


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    op.execute(
        """
        CREATE OR REPLACE VIEW v_creator_latest AS
        SELECT DISTINCT ON (platform, platform_creator_id) *
        FROM creator_snapshot
        ORDER BY platform, platform_creator_id, imported_at DESC, id DESC
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW v_xingtu_author_latest AS
        SELECT DISTINCT ON (star_id) *
        FROM xingtu_author_snapshot
        ORDER BY star_id, imported_at DESC, id DESC
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW v_ks_feigua_blogger_latest AS
        SELECT DISTINCT ON (blogger_id) *
        FROM ks_feigua_blogger_profile
        ORDER BY blogger_id, imported_at DESC, id DESC
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW v_magnetic_star_latest AS
        SELECT *
        FROM magnetic_dim_star
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW v_data_asset_status AS
        SELECT platform, asset_type, import_status, COUNT(*) AS asset_count, SUM(file_size) AS total_size
        FROM data_asset
        GROUP BY platform, asset_type, import_status
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW v_task_status AS
        SELECT platform, task_type, status, COUNT(*) AS task_count, MAX(created_at) AS latest_created_at
        FROM crawler_task
        GROUP BY platform, task_type, status
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_task_status")
    op.execute("DROP VIEW IF EXISTS v_data_asset_status")
    op.execute("DROP VIEW IF EXISTS v_magnetic_star_latest")
    op.execute("DROP VIEW IF EXISTS v_ks_feigua_blogger_latest")
    op.execute("DROP VIEW IF EXISTS v_xingtu_author_latest")
    op.execute("DROP VIEW IF EXISTS v_creator_latest")
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
