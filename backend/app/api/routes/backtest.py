from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from app.services.trading_service import trading_service
from app.engine.backtesting_engine import backtesting_engine
from app.domain.contracts import MarketCandle

router = APIRouter(prefix="/backtest")

class BacktestRequest(BaseModel):
    strategy: str = "alpha_hunter_v2"
    symbol: str = "BEL"
    period: str = "1y"

@router.post("/run")
def run_strategy_backtest(req: BacktestRequest):
    symbol = req.symbol.upper()
    
    # Calculate start date based on period
    to_date = datetime.now(timezone.utc).date()
    days = 365
    if req.period == "5y":
        days = 365 * 5
    elif req.period == "3y":
        days = 365 * 3
    elif req.period == "6m":
        days = 180
    elif req.period == "1mo":
        days = 30
        
    from_date = to_date - timedelta(days=days)
    
    # Fetch EOD records
    records = trading_service.security_archives(
        symbol=symbol,
        from_date=from_date,
        to_date=to_date,
        series="EQ",
        use_live=True
    )
    
    if not records:
        # Fallback to demo database candles from trading_service
        quotes = trading_service.get_live_quotes([symbol])
        if quotes:
            # Generate candles list from quote sector
            # We construct mock candles
            pass
        else:
            raise HTTPException(status_code=404, detail=f"No EOD data found for symbol {symbol}")
            
    # Convert SecurityArchiveRecord to MarketCandle contracts for backtester
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
        
    result = backtesting_engine.run_backtest(symbol, candles)
    return result
