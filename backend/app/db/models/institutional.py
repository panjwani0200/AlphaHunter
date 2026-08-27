from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Date, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum as SQLEnum

from app.db.base import Base
from app.db.models.enums import InvestorType, MarketSegment, enum_values
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class FiiData(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fii_data"
    __table_args__ = (
        UniqueConstraint(
            "observed_date",
            "investor_type",
            "market_segment",
            "source",
            name="uq_fii_data_date_investor_segment_source",
        ),
        Index("ix_fii_data_observed_investor_segment", "observed_date", "investor_type", "market_segment"),
    )

    observed_date: Mapped[date] = mapped_column(Date, nullable=False)
    investor_type: Mapped[InvestorType] = mapped_column(
        SQLEnum(
            InvestorType,
            name="investor_type",
            native_enum=False,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    market_segment: Mapped[MarketSegment] = mapped_column(
        SQLEnum(
            MarketSegment,
            name="market_segment",
            native_enum=False,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    buy_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    sell_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    net_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    buy_contracts: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sell_contracts: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    net_contracts: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

