from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SQLEnum

from app.db.base import Base
from app.db.models.enums import ContractType, TrendDirection, enum_values
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.options import OiSnapshot
    from app.db.models.trades import Position


class Stock(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stocks"
    __table_args__ = (
        Index("ix_stocks_sector_active", "sector", "is_active"),
        Index("ix_stocks_instrument_type_active", "instrument_type", "is_active"),
    )

    symbol: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    nse_symbol: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    isin: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    instrument_type: Mapped[ContractType] = mapped_column(
        SQLEnum(
            ContractType,
            name="contract_type",
            native_enum=False,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    sector: Mapped[str | None] = mapped_column(String(120), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(160), nullable=True)
    lot_size: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    tick_size: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    is_fno: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    source_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )

    market_snapshots: Mapped[list["MarketSnapshot"]] = relationship(
        "MarketSnapshot",
        back_populates="stock",
    )
    oi_snapshots: Mapped[list["OiSnapshot"]] = relationship("OiSnapshot", back_populates="stock")
    positions: Mapped[list["Position"]] = relationship("Position", back_populates="stock")


class MarketSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "market_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "stock_id",
            "timeframe",
            "observed_at",
            "source",
            name="uq_market_snapshots_stock_timeframe_observed_source",
        ),
        Index("ix_market_snapshots_stock_observed", "stock_id", "observed_at"),
        Index("ix_market_snapshots_symbol_observed", "symbol", "observed_at"),
        Index("ix_market_snapshots_observed_at_brin", "observed_at", postgresql_using="brin"),
    )

    stock_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("stocks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False, server_default="1d")
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    open_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    high_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    low_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    close_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    previous_close: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    vwap: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    change_percent: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    gap_percent: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    average_volume_20d: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    delivery_quantity: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    delivery_percent: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    turnover: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    atr_14: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    indicators: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    stock: Mapped[Stock] = relationship("Stock", back_populates="market_snapshots")


class SectorStrength(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sector_strength"
    __table_args__ = (
        UniqueConstraint(
            "sector",
            "observed_at",
            "source",
            name="uq_sector_strength_sector_observed_source",
        ),
        Index("ix_sector_strength_observed_score", "observed_at", "score"),
        Index("ix_sector_strength_sector_observed", "sector", "observed_at"),
    )

    sector: Mapped[str] = mapped_column(String(120), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    trend: Mapped[TrendDirection] = mapped_column(
        SQLEnum(
            TrendDirection,
            name="trend_direction",
            native_enum=False,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    relative_strength: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    advance_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decline_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unchanged_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    volume_ratio: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    leadership_symbols: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
