from app.domain.contracts import MarketCandle, SMCResult

def analyze_smc(candles: list[MarketCandle]) -> SMCResult:
    if len(candles) < 10:
        return SMCResult(smc_score=50, signal="NEUTRAL")
        
    recent = candles[-10:]
    latest = recent[-1]
    _ = recent[-2]
    
    # 1. Detect Bullish Displacement (Strong momentum candle)
    bullish_displacement = latest.close > latest.open and (latest.close - latest.open) > (latest.high - latest.low) * 0.7
    bearish_displacement = latest.close < latest.open and (latest.open - latest.close) > (latest.high - latest.low) * 0.7

    # 2. Detect Liquidity Sweep (Sweeping below recent low and closing above it)
    recent_low = min(c.low for c in candles[-20:-1])
    recent_high = max(c.high for c in candles[-20:-1])
    
    bullish_sweep = latest.low < recent_low and latest.close > recent_low
    bearish_sweep = latest.high > recent_high and latest.close < recent_high
    
    # 3. Detect Break of Structure (BOS)
    bos_up = latest.close > recent_high and bullish_displacement
    bos_down = latest.close < recent_low and bearish_displacement

    # Scoring
    score = 50
    signal = "NEUTRAL"
    
    if bos_up:
        score = 90 if bullish_sweep else 85
        signal = "BULLISH_BOS"
    elif bullish_sweep and bullish_displacement:
        score = 80
        signal = "BULLISH_SWEEP"
    elif bos_down:
        score = 90 if bearish_sweep else 85
        signal = "BEARISH_BOS"
    elif bearish_sweep and bearish_displacement:
        score = 80
        signal = "BEARISH_SWEEP"
        
    return SMCResult(smc_score=score, signal=signal)
