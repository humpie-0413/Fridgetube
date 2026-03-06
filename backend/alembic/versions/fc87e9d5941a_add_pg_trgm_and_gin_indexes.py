"""add_pg_trgm_and_gin_indexes

Revision ID: fc87e9d5941a
Revises: 544ca4dbe20f
Create Date: 2026-03-07 06:27:49.935454

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'fc87e9d5941a'
down_revision: Union[str, Sequence[str], None] = '544ca4dbe20f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pg_trgm extension
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # tsvector GIN indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_channel_video_tsv_title "
        "ON channel_video_index USING GIN (tsv_title)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_channel_video_tsv_desc "
        "ON channel_video_index USING GIN (tsv_description)"
    )

    # pg_trgm GIN indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_channel_video_title_trgm "
        "ON channel_video_index USING GIN (title gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_dish_name_trgm "
        "ON dish_name_master USING GIN (name gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ingredient_name_trgm "
        "ON ingredient_master USING GIN (name gin_trgm_ops)"
    )

    # expires_at indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_yt_snapshot_expires "
        "ON youtube_video_snapshot (expires_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_channel_video_expires "
        "ON channel_video_index (expires_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_channel_video_expires")
    op.execute("DROP INDEX IF EXISTS idx_yt_snapshot_expires")
    op.execute("DROP INDEX IF EXISTS idx_ingredient_name_trgm")
    op.execute("DROP INDEX IF EXISTS idx_dish_name_trgm")
    op.execute("DROP INDEX IF EXISTS idx_channel_video_title_trgm")
    op.execute("DROP INDEX IF EXISTS idx_channel_video_tsv_desc")
    op.execute("DROP INDEX IF EXISTS idx_channel_video_tsv_title")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
