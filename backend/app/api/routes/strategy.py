from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from app.services.trading_service import trading_service
from app.engine.backtesting_engine import backtesting_engine
from app.domain.contracts import MarketCandle

router = APIRouter(prefix="/strategy")

class CustomStrategyRequest(BaseModel):
    symbol: str = "BEL"
    rsi_min: float = 55.0
    volume_mult: float = 1.5
    trend_ma: int = 20

@router.post("/backtest")
def backtest_custom_rules(req: CustomStrategyRequest):
    symbol = req.symbol.upper()
    
    # Fetch 1 year of daily candles
    to_date = datetime.now(timezone.utc).date()
    from_date = to_date - timedelta(days=365)
    
    records = trading_service.security_archives(
        symbol=symbol,
        from_date=from_date,
        to_date=to_date,
        series="EQ",
        use_live=True
    )
    
    if not records:
        raise HTTPException(status_code=404, detail=f"No EOD data found for symbol {symbol}")
        
    candles = []
    for r in records:
        candles.append(MarketCandle(
            symbol=symbol,
            observed_at=datetime.combine(r.trade_date, datetime.min.time(), tzinfo=timezone.utc),
            open=r.open_price or 0.0,
            high=r.high_price or 0.0,
            low=r.low_price or 0.0,
            close=r.close_price or 0.0,
            volume=r.total_traded_quantity or 0,
            delivery_percent=r.delivery_to_traded_percent
        ))
        
    rules = {
        "rsi_min": req.rsi_min,
        "volume_mult": req.volume_mult,
        "trend_ma": req.trend_ma
    }
    
    result = backtesting_engine.run_backtest(symbol, candles, strategy_rules=rules)
    return result
