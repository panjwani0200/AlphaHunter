from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, Float, Index, Integer, String, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class BhavCopyDaily(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bhav_copy_daily"
    __table_args__ = (
        Index("ix_bhav_copy_symbol_date", "symbol", "date", unique=True),
    )

    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    
    open_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    close_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    oi: Mapped[int | None] = mapped_column(Integer, nullable=True)


class MarketStructureCache(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "market_structure_cache"
    __table_args__ = (
        Index("ix_market_structure_symbol", "symbol", unique=True),
    )

    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    
    monthly_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    monthly_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    high_52w: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_52w: Mapped[float | None] = mapped_column(Float, nullable=True)
