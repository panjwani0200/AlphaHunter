from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum as SQLEnum

from app.db.base import Base
from app.db.models.enums import AlertSeverity, AlertStatus, AlertType, enum_values
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Alert(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_alerts_dedupe_key"),
        Index("ix_alerts_type_status_triggered", "alert_type", "status", "triggered_at"),
        Index("ix_alerts_symbol_triggered", "symbol", "triggered_at"),
        Index("ix_alerts_triggered_at_brin", "triggered_at", postgresql_using="brin"),
    )

    stock_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("stocks.id", ondelete="RESTRICT"),
        nullable=True,
    )
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    alert_type: Mapped[AlertType] = mapped_column(
        SQLEnum(
            AlertType,
            name="alert_type",
            native_enum=False,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        SQLEnum(
            AlertSeverity,
            name="alert_severity",
            native_enum=False,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    status: Mapped[AlertStatus] = mapped_column(
        SQLEnum(
            AlertStatus,
            name="alert_status",
            native_enum=False,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        server_default=AlertStatus.PENDING.value,
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    channel: Mapped[str] = mapped_column(String(40), nullable=False, server_default="telegram")
    dedupe_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

