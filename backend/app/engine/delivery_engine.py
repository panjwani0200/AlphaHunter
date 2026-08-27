from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.bhavcopy import BhavCopyDaily


class DeliveryEngine:
    def __init__(self, db_session: Session):
        self.db = db_session

    def analyze_delivery(self, symbol: str, target_date: date) -> dict[str, Any]:
        """
        Calculates delivery statistics for a given stock up to the target date.
        """
        stmt = (
            select(BhavCopyDaily.delivery_pct, BhavCopyDaily.volume)
            .where(BhavCopyDaily.symbol == symbol)
            .where(BhavCopyDaily.date <= target_date)
            .order_by(BhavCopyDaily.date.desc())
            .limit(30)
        )
        records = self.db.execute(stmt).fetchall()
        
        if not records:
            return {}

        today_del_pct = records[0][0] or 0.0
        today_vol = records[0][1] or 0
        
        avg_30d_del_pct = sum((r[0] or 0.0) for r in records) / len(records) if records else 0.0
        spike = today_del_pct - avg_30d_del_pct
        
        inference = "Neutral"
        if today_del_pct > 65 and spike > 15:
            inference = "Strong Accumulation Profile"
        elif today_del_pct < 30 and today_vol > 0:
            inference = "High Speculation / Intraday Activity"

        return {
            "avg_30d_delivery": round(avg_30d_del_pct, 2),
            "last_day_delivery": round(today_del_pct, 2),
            "spike": round(spike, 2),
            "inference": inference,
        }
