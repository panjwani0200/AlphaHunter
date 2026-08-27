from app.domain.contracts import MarketCandle, TrendResult
from app.engine.technicals import _ema

def analyze_trend(candles: list[MarketCandle]) -> TrendResult:
    if len(candles) < 200:
        return TrendResult(trend="NEUTRAL", strength=0)

    closes = [candle.close for candle in candles]
    ema_20 = _ema(closes, 20)
    ema_50 = _ema(closes, 50)
    ema_200 = _ema(closes, 200)

    if ema_20 is None or ema_50 is None or ema_200 is None:
        return TrendResult(trend="NEUTRAL", strength=0)

    latest_price = closes[-1]
    
    # Check Higher Highs / Higher Lows over last 20 candles
    recent = candles[-20:]
    highs = [c.high for c in recent]
    lows = [c.low for c in recent]
    
    # Simple check for higher highs/lows
    higher_highs = highs[-1] > max(highs[:10])
    higher_lows = lows[-1] > min(lows[:10])
    
    lower_highs = highs[-1] < min(highs[:10])
    lower_lows = lows[-1] < min(lows[:10])

    is_bullish = latest_price > ema_20 and ema_20 > ema_50 and ema_50 > ema_200 and higher_highs and higher_lows
    is_bearish = latest_price < ema_20 and ema_20 < ema_50 and ema_50 < ema_200 and lower_highs and lower_lows

    if is_bullish:
        # Calculate strength based on distance from EMA
        dist = (latest_price - ema_200) / ema_200 * 100
        strength = min(100, 75 + int(dist * 2))
        return TrendResult(trend="BULLISH", strength=strength)
    elif is_bearish:
        dist = (ema_200 - latest_price) / ema_200 * 100
        strength = min(100, 75 + int(dist * 2))
        return TrendResult(trend="BEARISH", strength=strength)
    else:
        return TrendResult(trend="NEUTRAL", strength=50)
