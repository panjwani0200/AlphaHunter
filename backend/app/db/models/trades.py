from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SQLEnum

from app.db.base import Base
from app.db.models.enums import ContractType, OptionType, PositionSide, PositionStatus, TradeResult, enum_values
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.market import Stock


class Position(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "positions"
    __table_args__ = (
        Index("ix_positions_status_symbol", "status", "symbol"),
        Index("ix_positions_symbol_opened", "symbol", "opened_at"),
        Index("ix_positions_expiry_status", "expiry_date", "status"),
    )

    stock_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("stocks.id", ondelete="RESTRICT"),
        nullable=True,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
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
    side: Mapped[PositionSide] = mapped_column(
        SQLEnum(
            PositionSide,
            name="position_side",
            native_enum=False,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    status: Mapped[PositionStatus] = mapped_column(
        SQLEnum(
            PositionStatus,
            name="position_status",
            native_enum=False,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        server_default=PositionStatus.OPEN.value,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    target_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    option_type: Mapped[OptionType | None] = mapped_column(
        SQLEnum(
            OptionType,
            name="option_type",
            native_enum=False,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=True,
    )
    strike_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_health_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    latest_reversal_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    thesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    risk_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )

    stock: Mapped["Stock | None"] = relationship("Stock", back_populates="positions")


class TradeHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trade_history"
    __table_args__ = (
        Index("ix_trade_history_symbol_entry", "symbol", "entry_time"),
        Index("ix_trade_history_setup_result", "setup_type", "result"),
        Index("ix_trade_history_position", "position_id"),
    )

    stock_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("stocks.id", ondelete="RESTRICT"),
        nullable=True,
    )
    position_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="SET NULL"),
        nullable=True,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    setup_type: Mapped[str] = mapped_column(String(80), nullable=False)
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
    side: Mapped[PositionSide] = mapped_column(
        SQLEnum(
            PositionSide,
            name="position_side",
            native_enum=False,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    pnl_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    pnl_percent: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    result: Mapped[TradeResult | None] = mapped_column(
        SQLEnum(
            TradeResult,
            name="trade_result",
            native_enum=False,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=True,
    )
    max_favorable_excursion: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    max_adverse_excursion: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    entry_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    exit_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    lessons: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
