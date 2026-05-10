"""SQLAlchemy ORM models for business_needs, id_counters, and nlp_cache tables."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


class BusinessNeed(Base):
    """A single business need submitted through the sourcing form.

    ``tags`` holds objectif / domaine / impact / origine (with per-field confidence).
    ``confidence`` is an optional flattened snapshot of those confidence levels for querying.
    ``risks``, ``justifications``, and ``ivi_scores`` are filled by the latest gap analysis run.
    """

    __tablename__ = "business_needs"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    pitch: Mapped[str] = mapped_column(Text, nullable=False)
    horizon: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    confidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    constraints: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    risks: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    justifications: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    ivi_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    rework_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    duplicate_matches: Mapped[list] = mapped_column(JSONB, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("idx_bn_status", "status"),
        Index("idx_bn_created", "created_at"),
    )


class IdCounter(Base):
    """Year-scoped counter for BN-YYYY-NNN ID generation."""

    __tablename__ = "id_counters"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    counter: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class NlpCache(Base):
    """Persistent cache for LLM tagging results — survives container restarts.

    Key = SHA-256 of (pitch.strip().lower() + "|" + (horizon or "")).
    TTL enforced at read time by the service layer (default 24 h).
    """

    __tablename__ = "nlp_cache"

    cache_key: Mapped[str] = mapped_column(Text, primary_key=True)
    pitch: Mapped[str] = mapped_column(Text, nullable=False)
    horizon: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    suggestions_json: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
