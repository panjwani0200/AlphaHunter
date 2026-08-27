from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum as SQLEnum

from app.db.base import Base
from app.db.models.enums import ScannerSignalType, enum_values
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ScannerResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scanner_results"
    __table_args__ = (
        UniqueConstraint(
            "scan_run_id",
            "scanner_type",
            "symbol",
            "signal_type",
            name="uq_scanner_results_run_type_symbol_signal",
        ),
        Index("ix_scanner_results_run_rank", "scan_run_id", "rank"),
        Index("ix_scanner_results_observed_signal_score", "observed_at", "signal_type", "score"),
        Index("ix_scanner_results_symbol_observed", "symbol", "observed_at"),
    )

    scan_run_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    stock_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("stocks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scanner_type: Mapped[str] = mapped_column(String(80), nullable=False)
    signal_type: Mapped[ScannerSignalType] = mapped_column(
        SQLEnum(
            ScannerSignalType,
            name="scanner_signal_type",
            native_enum=False,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    price_breakout_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    oi_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    volume_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    futures_premium_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    rsi_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    option_chain_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    sector_strength_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    reasons: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    conflicts: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

