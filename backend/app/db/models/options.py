from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SQLEnum

from app.db.base import Base
from app.db.models.enums import ContractType, OiInterpretation, OptionType, enum_values
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.market import Stock


class OptionChainSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "option_chain_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "underlying_symbol",
            "observed_at",
            "expiry_date",
            "strike_price",
            "option_type",
            "source",
            name="uq_option_chain_contract_observed_source",
        ),
        Index("ix_option_chain_underlying_expiry_observed", "underlying_symbol", "expiry_date", "observed_at"),
        Index("ix_option_chain_observed_at_brin", "observed_at", postgresql_using="brin"),
        Index("ix_option_chain_oi", "underlying_symbol", "expiry_date", "option_type", "open_interest"),
    )

    underlying_stock_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("stocks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    underlying_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    strike_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    option_type: Mapped[OptionType] = mapped_column(
        SQLEnum(
            OptionType,
            name="option_type",
            native_enum=False,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    bid_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    ask_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    previous_close: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    change_percent: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    open_interest: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    change_in_open_interest: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    implied_volatility: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    delta: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    gamma: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    theta: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    vega: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    chain_metrics: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )


class OiSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "oi_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "observed_at",
            "contract_type",
            "expiry_date",
            "strike_price",
            "option_type",
            "source",
            name="uq_oi_snapshots_contract_observed_source",
        ),
        Index("ix_oi_snapshots_stock_observed", "stock_id", "observed_at"),
        Index("ix_oi_snapshots_symbol_observed", "symbol", "observed_at"),
        Index("ix_oi_snapshots_interpretation_observed", "interpretation", "observed_at"),
        Index("ix_oi_snapshots_observed_at_brin", "observed_at", postgresql_using="brin"),
    )

    stock_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("stocks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    contract_symbol: Mapped[str | None] = mapped_column(String(96), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    contract_type: Mapped[ContractType] = mapped_column(
        SQLEnum(
            ContractType,
            name="contract_type",
            native_enum=False,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    strike_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
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
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    underlying_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    contract_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    futures_premium: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    open_interest: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    change_in_open_interest: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    oi_change_percent: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    interpretation: Mapped[OiInterpretation | None] = mapped_column(
        SQLEnum(
            OiInterpretation,
            name="oi_interpretation",
            native_enum=False,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=True,
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    stock: Mapped["Stock"] = relationship("Stock", back_populates="oi_snapshots")
