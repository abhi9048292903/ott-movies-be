"""Prediction V2 columns on ott_dates."""

from alembic import op
import sqlalchemy as sa

revision = "0002_prediction_v2"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    existing = _columns("ott_dates")
    if "window_start" not in existing:
        op.add_column("ott_dates", sa.Column("window_start", sa.Date(), nullable=True))
    if "window_end" not in existing:
        op.add_column("ott_dates", sa.Column("window_end", sa.Date(), nullable=True))
    if "likely_platform_id" not in existing:
        op.add_column("ott_dates", sa.Column("likely_platform_id", sa.Integer(), nullable=True))
    if "platform_confidence" not in existing:
        op.add_column("ott_dates", sa.Column("platform_confidence", sa.Float(), nullable=True))
    if "generated_at" not in existing:
        op.add_column("ott_dates", sa.Column("generated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    existing = _columns("ott_dates")
    for name in ("generated_at", "platform_confidence", "likely_platform_id", "window_end", "window_start"):
        if name in existing:
            op.drop_column("ott_dates", name)
