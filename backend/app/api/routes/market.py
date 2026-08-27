import asyncio
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter
from fastapi import Query, HTTPException

from app.domain.contracts import (
    LiveQuote, MarketOverview, MarketSnapshot, SecurityArchiveRecord, 
    MarketRegime, SectorScore, EventRisk, MarketCandle
)
from app.services.trading_service import trading_service

router = APIRouter(prefix="/market")


@router.get("/overview", response_model=MarketOverview)
async def market_overview() -> MarketOverview:
    return await trading_service.market_overview()


@router.get("/snapshots", response_model=list[MarketSnapshot])
async def market_snapshots() -> list[MarketSnapshot]:
    return await trading_service.get_snapshots()


@router.get("/regime", response_model=MarketRegime)
async def market_regime() -> MarketRegime:
    return await trading_service.get_market_regime()


@router.get("/sectors", response_model=list[SectorScore])
async def sector_scores() -> list[SectorScore]:
    return await trading_service.get_sector_scores()


@router.get("/event-risk/{symbol}", response_model=EventRisk)
async def event_risk(symbol: str) -> EventRisk:
    # get_event_risk is synchronous, but we'll await if we changed it. Wait, I didn't change get_event_risk, it doesn't call get_snapshots.
    return trading_service.get_event_risk(symbol)


@router.get("/quotes/live", response_model=list[LiveQuote])
def live_quotes(
    symbols: str | None = Query(
        default=None,
        description="Comma-separated list of NSE symbols. Defaults to all tracked symbols.",
    )
) -> list[LiveQuote]:
    """
    Real-time quotes from NSE when live mode is enabled, otherwise from
    the latest in-memory snapshot (always returns data).
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()] if symbols else None
    return trading_service.get_live_quotes(symbols=symbol_list)


@router.get("/intraday", response_model=list[MarketCandle])
def intraday_data(
    symbol: str = Query(..., min_length=1, max_length=32),
    interval: str = Query(default="5m")
) -> list[MarketCandle]:
    """
    Fetch real intraday market data (1m, 5m, 15m, 1h) for a symbol using the active market data provider.
    """
    try:
        return trading_service.get_intraday_data(symbol=symbol, interval=interval)
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch intraday data: {str(e)}")


# ── In-memory lookup cache (symbol+range → records, TTL 60s) ──────────────
_lookup_cache: dict[str, tuple[float, list]] = {}
_LOOKUP_TTL = 60.0  # seconds


@router.get("/security-archives", response_model=list[SecurityArchiveRecord])
async def security_archives(
    symbol: str = Query(..., min_length=1, max_length=32),
    series: str = Query(default="ALL", min_length=2, max_length=8),
    from_date: date | None = None,
    to_date: date | None = None,
    range: str = Query(default="3M", pattern="^(1D|1W|1M|3M|6M|1Y|5Y|CUSTOM)$"),
    live: bool = Query(default=False),
) -> list[SecurityArchiveRecord]:
    import time
    end_date = to_date or datetime.now(timezone.utc).date()
    start_date = from_date or _start_date_for_range(end_date, range)
    cache_key = f"{symbol.upper()}:{range}:{live}"
    now = time.monotonic()

    # Return cached result if fresh
    if cache_key in _lookup_cache:
        ts, cached = _lookup_cache[cache_key]
        if now - ts < _LOOKUP_TTL:
            return cached

    # Run the blocking service call in a thread so the event loop stays free
    result = await asyncio.to_thread(
        trading_service.security_archives,
        symbol=symbol,
        from_date=start_date,
        to_date=end_date,
        series=series,
        use_live=live,
    )
    _lookup_cache[cache_key] = (now, result)
    return result


def _start_date_for_range(end_date: date, range_value: str) -> date:
    days = {
        "1D": 1,
        "1W": 7,
        "1M": 30,
        "3M": 90,
        "6M": 180,
        "1Y": 365,
        "5Y": 365 * 5,
        "CUSTOM": 90,
    }[range_value]
    return end_date - timedelta(days=days)
# ── Institutional metrics cache (symbol → data, TTL 5 min) ───────────────
_inst_cache: dict[str, tuple[float, dict]] = {}
_INST_TTL = 300.0  # 5 minutes


@router.get("/institutional-metrics/{symbol}")
async def institutional_metrics(symbol: str) -> dict:
    import time
    cache_key = symbol.upper()
    now = time.monotonic()
    if cache_key in _inst_cache:
        ts, cached = _inst_cache[cache_key]
        if now - ts < _INST_TTL:
            return cached

    from app.engine.delivery_engine import DeliveryEngine
    from app.engine.market_structure_engine import MarketStructureEngine
    from app.engine.fibonacci_engine import FibonacciEngine
    from app.engine.spurt_engine import SpurtEngine
    from app.db.session import SessionLocal
    
    def _compute() -> dict:
        with SessionLocal() as db_session:
            del_engine = DeliveryEngine(db_session)
            struct_engine = MarketStructureEngine(db_session)
            fib_engine = FibonacciEngine()
            spurt_engine = SpurtEngine()
            
            quotes = trading_service.get_live_quotes([symbol])
            current_price = quotes[0].last_price if quotes else 0.0
            
            struct_data = struct_engine.analyze_structure(symbol, current_price)
            fib_data = fib_engine.compute_levels(current_price * 1.05, current_price * 0.95, trend="UP")
            fib_confluence = fib_engine.find_confluence(current_price, fib_data, threshold_pct=1.0)
            del_data = del_engine.analyze_delivery(symbol, datetime.now(timezone.utc).date())
            
            opt_data = {
                "support": current_price * 0.9,
                "resistance": current_price * 1.1,
                "expiry_range": f"{current_price * 0.9:.2f} - {current_price * 1.1:.2f}",
                "bullish_probability": 65,
                "max_pain": current_price,
            }
            
            spurt_data = spurt_engine.evaluate_spurt(
                symbol, 
                today_volume=1000000, avg_20d_volume=500000, 
                today_delivery=45.0, avg_30d_delivery=30.0, 
                today_change_pct=2.5, oi_interpretation=None, near_breakout=True
            )

            return {
                "symbol": symbol,
                "structure": struct_data,
                "fibonacci": {
                    "levels": fib_data,
                    "confluence": fib_confluence,
                },
                "delivery": del_data,
                "options": opt_data,
                "spurt": spurt_data,
            }

    result = await asyncio.to_thread(_compute)
    _inst_cache[cache_key] = (now, result)
    return result


@router.get("/news")
async def get_market_news(
    symbol: str | None = Query(default=None, description="Filter by stock symbol")
) -> list[dict]:
    import yfinance as yf
    
    def fetch_yf_news(sym: str) -> list[dict]:
        try:
            return yf.Ticker(sym).news or []
        except Exception:
            return []

    symbols_to_fetch = []
    if symbol:
        yf_symbol = "^NSEI" if symbol.upper() == "NIFTY" else f"{symbol.upper()}.NS"
        symbols_to_fetch.append((symbol.upper(), yf_symbol))
    else:
        # Fetch top running stocks of the day!
        snapshots = await trading_service.get_snapshots()
        top_stocks = sorted(
            [s for s in snapshots if s.change_percent is not None],
            key=lambda x: x.change_percent, 
            reverse=True
        )[:3]
        
        top_symbols = [s.symbol for s in top_stocks]
        if not top_symbols:
            top_symbols = ["RELIANCE", "HDFCBANK", "INFY"]
            
        for sym in top_symbols:
            symbols_to_fetch.append((sym, f"{sym}.NS"))
        # Always include general market news
        symbols_to_fetch.append(("NIFTY", "^NSEI"))

    # Concurrently fetch all news
    tasks = [asyncio.to_thread(fetch_yf_news, yf_sym) for _, yf_sym in symbols_to_fetch]
    news_results = await asyncio.gather(*tasks)

    results = []
    bull_words = {"surge", "up", "buy", "profit", "gain", "high", "growth", "jump", "positive", "expand", "record", "beat", "dividend", "bonus"}
    bear_words = {"fall", "down", "loss", "drop", "decline", "negative", "underperform", "low", "miss", "shrink", "crash", "sell", "penalty"}
    
    for (display_sym, _), raw_news in zip(symbols_to_fetch, news_results):
        for item in raw_news:
            content = item.get("content", {}) if "content" in item else item
            title = content.get("title", "")
            summary = content.get("summary", "")
            
            text = (title + " " + summary).lower()
            b_score = sum(1 for w in bull_words if w in text)
            r_score = sum(1 for w in bear_words if w in text)
            
            sentiment, score = "NEUTRAL", 50
            if b_score > r_score:
                sentiment, score = "BULLISH", min(100, 75 + (b_score * 5))
            elif r_score > b_score:
                sentiment, score = "BEARISH", max(0, 25 - (r_score * 5))
                
            pub_date = content.get("pubDate", datetime.now(timezone.utc).isoformat())
            
            results.append({
                "title": title,
                "summary": summary,
                "sentiment": sentiment,
                "sentiment_score": score,
                "symbol": display_sym,
                "timestamp": pub_date
            })
            
    # Sort all aggregated news by timestamp descending (newest first)
    results.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return results[:20]


@router.get("/spurts")
async def get_market_spurts() -> dict:
    snapshots = await trading_service.get_snapshots()
    regime = await trading_service.get_market_regime()
    
    volume_spurts = []
    delivery_spurts = []
    
    for s in snapshots:
        avg_vol = s.average_volume_20d or 1
        vol_spurt = round(s.volume / avg_vol, 2)
        
        if vol_spurt >= 1.5:
            volume_spurts.append({
                "symbol": s.symbol,
                "price": s.last_price,
                "volume_spurt": vol_spurt,
                "volume": s.volume,
                "average_volume_20d": s.average_volume_20d,
                "change_percent": s.change_percent
            })
            
        del_pct = s.delivery_percent or 0.0
        if del_pct >= 40.0:
            oi_interpretation = "Long Build-up" if s.change_percent > 0 else "Short Covering"
            delivery_spurts.append({
                "symbol": s.symbol,
                "price": s.last_price,
                "delivery_percent": del_pct,
                "oi_interpretation": oi_interpretation,
                "regime": regime.regime.replace("_", " ").upper(),
                "change_percent": s.change_percent
            })
            
    volume_spurts.sort(key=lambda x: x["volume_spurt"], reverse=True)
    delivery_spurts.sort(key=lambda x: x["delivery_percent"], reverse=True)
    
    return {
        "volume_spurts": volume_spurts,
        "delivery_spurts": delivery_spurts
    }

