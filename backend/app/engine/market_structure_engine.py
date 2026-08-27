from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.bhavcopy import MarketStructureCache


class MarketStructureEngine:
    def __init__(self, db_session: Session):
        self.db = db_session

    def analyze_structure(self, symbol: str, current_price: float) -> dict[str, Any]:
        """
        Analyzes the market structure for a given stock using cached 52W and Monthly highs/lows.
        """
        stmt = select(MarketStructureCache).where(MarketStructureCache.symbol == symbol)
        cache = self.db.scalars(stmt).first()

        if not cache:
            try:
                import yfinance as yf
                # Map standard symbols for yfinance
                if symbol == "NIFTY":
                    ticker_name = "^NSEI"
                elif symbol == "BANKNIFTY":
                    ticker_name = "^NSEBANK"
                elif symbol == "TATAMOTORS":
                    ticker_name = "TMCV.NS"
                elif symbol == "LTIM":
                    ticker_name = "LTM.NS"
                else:
                    ticker_name = f"{symbol}.NS"

                ticker = yf.Ticker(ticker_name)
                hist = ticker.history(period="1y")
                
                if not hist.empty:
                    high_52w = float(hist['High'].max())
                    low_52w = float(hist['Low'].min())
                    
                    # Approximating last month as last 30 calendar days of trading data (roughly 22 trading days)
                    last_month = hist.tail(22)
                    monthly_high = float(last_month['High'].max()) if not last_month.empty else current_price
                    monthly_low = float(last_month['Low'].min()) if not last_month.empty else current_price
                else:
                    monthly_high = monthly_low = high_52w = low_52w = current_price
            except Exception:
                return {}
        else:
            monthly_high = cache.monthly_high or current_price
            monthly_low = cache.monthly_low or current_price
            high_52w = cache.high_52w or current_price
            low_52w = cache.low_52w or current_price

        # Calculate distances
        distance_to_month_high = round(((current_price - monthly_high) / monthly_high) * 100, 2)
        distance_to_month_low = round(((current_price - monthly_low) / monthly_low) * 100, 2)
        distance_to_52w_high = round(((current_price - high_52w) / high_52w) * 100, 2)
        
        flags = []
        if distance_to_52w_high > -3.0:
            flags.append("Near 52W High (<3%)")
        if distance_to_52w_high >= 0:
            flags.append("Fresh 52W Breakout")
            
        if distance_to_month_high > -2.0:
            flags.append("Near Monthly High Breakout")
        if distance_to_month_low < 2.0:
            flags.append("Near Monthly Low Breakdown")

        return {
            "monthly_high": monthly_high,
            "monthly_low": monthly_low,
            "distance_to_month_high_pct": distance_to_month_high,
            "distance_to_month_low_pct": distance_to_month_low,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "distance_to_52w_high_pct": distance_to_52w_high,
            "flags": flags,
        }
