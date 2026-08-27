from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.bhavcopy import BhavCopyDaily


class BhavCopyEngine:
    def __init__(self, db_session: Session):
        self.db = db_session

    def process_bhavcopy_data(self, records: list[dict[str, Any]]) -> None:
        """
        Ingest daily bhavcopy records into the database.
        Expected keys in record: symbol, date, open, high, low, close, volume, delivery_qty, delivery_pct, oi
        """
        for record in records:
            obj = BhavCopyDaily(
                symbol=record.get("symbol"),
                date=record.get("date"),
                open_price=record.get("open"),
                high_price=record.get("high"),
                low_price=record.get("low"),
                close_price=record.get("close"),
                volume=record.get("volume"),
                delivery_qty=record.get("delivery_qty"),
                delivery_pct=record.get("delivery_pct"),
                oi=record.get("oi"),
            )
            self.db.add(obj)
        self.db.commit()

    def analyze_eod(self, symbol: str, target_date: date) -> dict[str, Any]:
        """
        Analyze a specific stock's EOD data to detect volume/delivery spikes.
        Requires historical data for averages (usually 20d vol, 30d delivery).
        """
        # Fetch recent records up to target date
        stmt = (
            select(BhavCopyDaily)
            .where(BhavCopyDaily.symbol == symbol)
            .where(BhavCopyDaily.date <= target_date)
            .order_by(BhavCopyDaily.date.desc())
            .limit(30)
        )
        records = self.db.scalars(stmt).all()
        
        if not records:
            return {}

        today = records[0]
        history = records[1:]
        
        if not history:
            return {
                "symbol": symbol,
                "volume_spike": 0,
                "delivery_spike": 0,
                "inference": "Insufficient history",
            }
            
        avg_vol_20d = sum(r.volume or 0 for r in history[:20]) / min(len(history), 20)
        avg_del_30d = sum(r.delivery_pct or 0 for r in history) / len(history)
        
        volume_spike = round((today.volume or 0) / avg_vol_20d, 2) if avg_vol_20d else 0.0
        delivery_spike = round((today.delivery_pct or 0) - avg_del_30d, 2) if avg_del_30d else 0.0
        
        inference = "Neutral"
        if volume_spike > 2.0 and delivery_spike > 15:
            if (today.close_price or 0) > (today.open_price or 0):
                inference = "Possible accumulation"
            else:
                inference = "Possible distribution"
        elif delivery_spike > 20 and volume_spike < 1.5:
            inference = "Silent buying/selling"

        return {
            "symbol": symbol,
            "volume_spike": volume_spike,
            "delivery_spike": delivery_spike,
            "inference": inference,
        }
