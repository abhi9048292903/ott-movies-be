from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Platform(Base):
    __tablename__ = "platforms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    availability: Mapped[list["MovieAvailability"]] = relationship(back_populates="platform")


class Movie(Base):
    __tablename__ = "movies"
    __table_args__ = (Index("ix_movies_language_country", "language", "country"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    overview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    poster_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    theatrical_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    language: Mapped[str] = mapped_column(String(16), default="en", index=True)
    country: Mapped[str] = mapped_column(String(8), default="IN", index=True)
    tmdb_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    availability: Mapped[list["MovieAvailability"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan"
    )
    ott: Mapped[Optional["OttDate"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan", uselist=False
    )


class MovieAvailability(Base):
    __tablename__ = "movie_availability"
    __table_args__ = (
        UniqueConstraint("movie_id", "platform_id", "region", "availability_type", name="uq_movie_platform_region_type"),
        Index("ix_movie_availability_movie_id", "movie_id"),
        Index("ix_movie_availability_platform_id", "platform_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id", ondelete="CASCADE"))
    region: Mapped[str] = mapped_column(String(8), default="IN")
    availability_type: Mapped[str] = mapped_column(String(16), default="stream")
    available_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="admin")

    movie: Mapped[Movie] = relationship(back_populates="availability")
    platform: Mapped[Platform] = relationship(back_populates="availability")


class OttDate(Base):
    __tablename__ = "ott_dates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), unique=True)
    status: Mapped[str] = mapped_column(String(24), default="unknown", index=True)
    announced_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    predicted_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    predicted_window_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    window_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    window_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    likely_platform_id: Mapped[Optional[int]] = mapped_column(ForeignKey("platforms.id"), nullable=True)
    platform_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    movie: Mapped[Movie] = relationship(back_populates="ott")
    likely_platform: Mapped[Optional[Platform]] = relationship(foreign_keys=[likely_platform_id])
