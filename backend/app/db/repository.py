from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from collections.abc import Callable
from uuid import UUID, uuid4

from sqlalchemy import select, text, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models.alerts import Alert as AlertRecord
from app.db.models.enums import (
    AlertSeverity,
    AlertStatus,
    AlertType as DbAlertType,
    ContractType,
    OptionType as DbOptionType,
    PositionSide,
    PositionStatus,
    ScannerSignalType,
)
from app.db.models.market import MarketSnapshot as MarketSnapshotRecord
from app.db.models.market import Stock
from app.db.models.scanner import ScannerResult
from app.db.models.security_archive import SecurityArchiveRecord as SecurityArchiveRecordModel
from app.db.models.trades import Position
from app.db.session import SessionLocal
from app.domain.contracts import (
    AlertAction,
    AlertMessage,
    MarketSnapshot,
    PositionState,
    ScannerCandidate,
    SecurityArchiveRecord,
)


class TradingRepository:
    def __init__(self) -> None:
        self._last_error: str | None = None

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def database_connected(self) -> bool:
        try:
            with SessionLocal() as session:
                session.execute(text("SELECT 1"))
            self._last_error = None
            return True
        except SQLAlchemyError as exc:
            self._last_error = str(exc)
            return False

    def save_market_snapshots(self, snapshots: list[MarketSnapshot]) -> None:
        self._execute(lambda session: self._save_market_snapshots(session, snapshots))

    def save_security_archives(self, records: list[SecurityArchiveRecord]) -> None:
        self._execute(lambda session: self._save_security_archives(session, records))

    def save_scanner_results(self, candidates: list[ScannerCandidate]) -> None:
        scan_run_id = uuid4()
        self._execute(lambda session: self._save_scanner_results(session, scan_run_id, candidates))

    def save_position(self, position: PositionState) -> None:
        self._execute(lambda session: self._save_position(session, position))

    def delete_position(self, position_id: str) -> None:
        self._execute(lambda session: self._delete_position(session, position_id))

    def load_open_positions(self) -> list[PositionState]:
        try:
            with SessionLocal() as session:
                records = session.scalars(
                    select(Position).where(Position.status == PositionStatus.OPEN)
                ).all()
                self._last_error = None
                return [self._position_record_to_state(record) for record in records]
        except SQLAlchemyError as exc:
            self._last_error = str(exc)
            return []

    def save_alert(self, alert: AlertMessage) -> None:
        self._execute(lambda session: self._save_alert(session, alert))

    def _execute(self, operation: Callable[[Session], None]) -> None:
        try:
            with SessionLocal() as session:
                operation(session)
                session.commit()
            self._last_error = None
        except SQLAlchemyError as exc:
            self._last_error = str(exc)

    def _save_market_snapshots(self, session: Session, snapshots: list[MarketSnapshot]) -> None:
        for snapshot in snapshots:
            stock = self._get_or_create_stock(session, snapshot.symbol, snapshot.sector)
            exists = session.scalar(
                select(MarketSnapshotRecord.id).where(
                    MarketSnapshotRecord.stock_id == stock.id,
                    MarketSnapshotRecord.timeframe == "1d",
                    MarketSnapshotRecord.observed_at == snapshot.observed_at,
                    MarketSnapshotRecord.source == snapshot.source,
                )
            )
            if exists:
                continue

            latest_candle = snapshot.candles[-1] if snapshot.candles else None
            session.add(
                MarketSnapshotRecord(
                    stock_id=stock.id,
                    symbol=snapshot.symbol,
                    observed_at=snapshot.observed_at,
                    timeframe="1d",
                    source=snapshot.source,
                    open_price=self._decimal(latest_candle.open if latest_candle else None),
                    high_price=self._decimal(latest_candle.high if latest_candle else None),
                    low_price=self._decimal(latest_candle.low if latest_candle else None),
                    close_price=self._decimal(latest_candle.close if latest_candle else None),
                    last_price=self._decimal(snapshot.last_price),
                    previous_close=self._decimal(snapshot.previous_close),
                    change_percent=self._decimal(snapshot.change_percent),
                    volume=snapshot.volume,
                    average_volume_20d=snapshot.average_volume_20d,
                    delivery_percent=self._decimal(snapshot.delivery_percent),
                    indicators={},
                    raw_payload=snapshot.model_dump(mode="json", exclude={"candles"}),
                )
            )

    def _save_security_archives(
        self,
        session: Session,
        records: list[SecurityArchiveRecord],
    ) -> None:
        for record in records:
            stock = self._get_or_create_stock(session, record.symbol)
            exists = session.scalar(
                select(SecurityArchiveRecordModel.id).where(
                    SecurityArchiveRecordModel.symbol == record.symbol,
                    SecurityArchiveRecordModel.series == record.series,
                    SecurityArchiveRecordModel.trade_date == record.trade_date,
                    SecurityArchiveRecordModel.source == record.source,
                )
            )
            if exists:
                continue

            session.add(
                SecurityArchiveRecordModel(
                    stock_id=stock.id,
                    symbol=record.symbol,
                    series=record.series,
                    trade_date=record.trade_date,
                    previous_close=self._decimal(record.previous_close),
                    open_price=self._decimal(record.open_price),
                    high_price=self._decimal(record.high_price),
                    low_price=self._decimal(record.low_price),
                    last_price=self._decimal(record.last_price),
                    close_price=self._decimal(record.close_price),
                    vwap=self._decimal(record.vwap),
                    total_traded_quantity=record.total_traded_quantity,
                    turnover=self._decimal(record.turnover),
                    number_of_trades=record.number_of_trades,
                    deliverable_quantity=record.deliverable_quantity,
                    delivery_to_traded_percent=self._decimal(record.delivery_to_traded_percent),
                    source=record.source,
                    raw_payload=record.model_dump(mode="json"),
                )
            )

    def _save_scanner_results(
        self,
        session: Session,
        scan_run_id: UUID,
        candidates: list[ScannerCandidate],
    ) -> None:
        observed_at = datetime.now(timezone.utc)
        for candidate in candidates:
            stock = self._get_or_create_stock(session, candidate.symbol)
            session.add(
                ScannerResult(
                    scan_run_id=scan_run_id,
                    stock_id=stock.id,
                    symbol=candidate.symbol,
                    observed_at=observed_at,
                    scanner_type="broad_market",
                    signal_type=ScannerSignalType(candidate.signal_type.value),
                    rank=candidate.rank,
                    score=self._decimal(candidate.score) or Decimal("0"),
                    price_breakout_score=self._decimal(candidate.price_breakout_score),
                    oi_score=self._decimal(candidate.oi_score),
                    volume_score=self._decimal(candidate.volume_score),
                    futures_premium_score=self._decimal(candidate.futures_premium_score),
                    rsi_score=self._decimal(candidate.rsi_score),
                    option_chain_score=self._decimal(candidate.option_chain_score),
                    sector_strength_score=self._decimal(candidate.sector_strength_score),
                    reasons=candidate.reasons,
                    conflicts=candidate.conflicts,
                    evidence=candidate.evidence,
                )
            )

    def _save_position(self, session: Session, position: PositionState) -> None:
        stock = self._get_or_create_stock(session, position.symbol)
        record_id = UUID(position.id)
        record = session.get(Position, record_id)
        values = {
            "stock_id": stock.id,
            "symbol": position.symbol,
            "instrument_type": ContractType(position.instrument_type.value),
            "side": PositionSide(position.side),
            "status": PositionStatus.OPEN,
            "quantity": position.quantity,
            "entry_price": self._decimal(position.entry_price) or Decimal("0"),
            "stop_loss": self._decimal(position.stop_loss),
            "target_price": self._decimal(position.target_price),
            "option_type": DbOptionType(position.option_type.value) if position.option_type else None,
            "strike_price": self._decimal(position.strike_price),
            "expiry_date": position.expiry_date,
            "opened_at": position.opened_at,
            "latest_health_score": self._decimal(position.health_score),
            "latest_reversal_score": self._decimal(position.reversal_score),
            "thesis": position.thesis,
            "tags": [],
            "risk_metadata": position.model_dump(mode="json"),
        }
        if record is None:
            session.add(Position(id=record_id, **values))
            return

        for key, value in values.items():
            setattr(record, key, value)

    def _delete_position(self, session: Session, position_id: str) -> None:
        stmt = delete(Position).where(Position.id == position_id)
        session.execute(stmt)

    def _save_alert(self, session: Session, alert: AlertMessage) -> None:
        stock = self._get_or_create_stock(session, alert.symbol) if alert.symbol else None
        dedupe_key = self._alert_dedupe_key(alert)
        exists = session.scalar(select(AlertRecord.id).where(AlertRecord.dedupe_key == dedupe_key))
        if exists:
            return

        session.add(
            AlertRecord(
                stock_id=stock.id if stock else None,
                symbol=alert.symbol,
                alert_type=DbAlertType(alert.alert_type.value),
                severity=self._severity_for_action(alert.action),
                status=AlertStatus.PENDING,
                title=alert.title,
                message=alert.message,
                score=self._decimal(alert.score),
                confidence=None,
                channel="telegram",
                dedupe_key=dedupe_key,
                triggered_at=alert.triggered_at,
                sent_at=None,
                acknowledged_at=None,
                payload=alert.payload,
            )
        )

    def _get_or_create_stock(
        self,
        session: Session,
        symbol: str,
        sector: str | None = None,
    ) -> Stock:
        normalized = symbol.upper()
        stock = session.scalar(select(Stock).where(Stock.symbol == normalized))
        if stock:
            if sector and stock.sector != sector:
                stock.sector = sector
            return stock

        stock = Stock(
            symbol=normalized,
            nse_symbol=normalized,
            name=normalized,
            instrument_type=ContractType.INDEX if "NIFTY" in normalized else ContractType.EQUITY,
            sector=sector,
            is_fno=normalized not in {"NIFTY"},
            is_active=True,
        )
        session.add(stock)
        session.flush()
        return stock

    def _position_record_to_state(self, record: Position) -> PositionState:
        metadata = record.risk_metadata or {}
        return PositionState(
            id=str(record.id),
            symbol=record.symbol,
            instrument_type=metadata.get("instrument_type", record.instrument_type.value),
            side=record.side.value,
            quantity=record.quantity,
            entry_price=float(record.entry_price),
            stop_loss=float(record.stop_loss) if record.stop_loss is not None else None,
            target_price=float(record.target_price) if record.target_price is not None else None,
            option_type=metadata.get("option_type"),
            strike_price=float(record.strike_price) if record.strike_price is not None else None,
            expiry_date=record.expiry_date,
            thesis=record.thesis,
            opened_at=record.opened_at,
            latest_price=metadata.get("latest_price"),
            pnl_percent=metadata.get("pnl_percent"),
            health_score=float(record.latest_health_score)
            if record.latest_health_score is not None
            else None,
            reversal_score=float(record.latest_reversal_score)
            if record.latest_reversal_score is not None
            else None,
            action=metadata.get("action", AlertAction.HOLD),
            reasons=metadata.get("reasons", []),
        )

    def _severity_for_action(self, action: AlertAction) -> AlertSeverity:
        if action == AlertAction.EXIT:
            return AlertSeverity.EXIT
        if action == AlertAction.REDUCE:
            return AlertSeverity.REDUCE
        if action == AlertAction.WATCH:
            return AlertSeverity.WARNING
        return AlertSeverity.INFO

    def _alert_dedupe_key(self, alert: AlertMessage) -> str:
        bucket = int(alert.triggered_at.timestamp() / 900)
        return f"{alert.alert_type.value}:{alert.symbol or 'market'}:{alert.action.value}:{alert.title}:{bucket}"

    def _decimal(self, value: float | int | None) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(round(float(value), 6)))
