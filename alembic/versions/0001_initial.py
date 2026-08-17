"""Initial OTT Radar schema (users, platforms, movies, availability, ott_dates)."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="admin"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "platforms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("logo_url", sa.String(500), nullable=True),
    )
    op.create_index("ix_platforms_slug", "platforms", ["slug"], unique=True)

    op.create_table(
        "movies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("poster_url", sa.String(500), nullable=True),
        sa.Column("theatrical_date", sa.Date(), nullable=True),
        sa.Column("language", sa.String(16), nullable=False, server_default="en"),
        sa.Column("country", sa.String(8), nullable=False, server_default="IN"),
        sa.Column("tmdb_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_movies_title", "movies", ["title"])
    op.create_index("ix_movies_theatrical_date", "movies", ["theatrical_date"])
    op.create_index("ix_movies_language", "movies", ["language"])
    op.create_index("ix_movies_country", "movies", ["country"])
    op.create_index("ix_movies_language_country", "movies", ["language", "country"])
    op.create_index("ix_movies_tmdb_id", "movies", ["tmdb_id"], unique=True)

    op.create_table(
        "movie_availability",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform_id", sa.Integer(), sa.ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("region", sa.String(8), nullable=False, server_default="IN"),
        sa.Column("availability_type", sa.String(16), nullable=False, server_default="stream"),
        sa.Column("available_from", sa.Date(), nullable=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="admin"),
        sa.UniqueConstraint("movie_id", "platform_id", "region", "availability_type", name="uq_movie_platform_region_type"),
    )
    op.create_index("ix_movie_availability_movie_id", "movie_availability", ["movie_id"])
    op.create_index("ix_movie_availability_platform_id", "movie_availability", ["platform_id"])

    op.create_table(
        "ott_dates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="unknown"),
        sa.Column("announced_date", sa.Date(), nullable=True),
        sa.Column("predicted_date", sa.Date(), nullable=True),
        sa.Column("predicted_window_days", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=True),
    )
    op.create_index("ix_ott_dates_movie_id", "ott_dates", ["movie_id"], unique=True)
    op.create_index("ix_ott_dates_status", "ott_dates", ["status"])


def downgrade() -> None:
    op.drop_table("ott_dates")
    op.drop_table("movie_availability")
    op.drop_table("movies")
    op.drop_table("platforms")
    op.drop_table("users")
