from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class SecurityArchiveRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "security_archive_records"
    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "series",
            "trade_date",
            "source",
            name="uq_security_archive_symbol_series_date_source",
        ),
        Index("ix_security_archive_symbol_date", "symbol", "trade_date"),
        Index("ix_security_archive_date_delivery", "trade_date", "delivery_to_traded_percent"),
        Index("ix_security_archive_trade_date_brin", "trade_date", postgresql_using="brin"),
    )

    stock_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("stocks.id", ondelete="RESTRICT"),
        nullable=True,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    series: Mapped[str] = mapped_column(String(8), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    previous_close: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    open_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    high_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    low_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    close_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    vwap: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    total_traded_quantity: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    turnover: Mapped[Decimal | None] = mapped_column(Numeric(24, 2), nullable=True)
    number_of_trades: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    deliverable_quantity: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    delivery_to_traded_percent: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

