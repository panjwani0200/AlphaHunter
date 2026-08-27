from app.domain.contracts import MarketRegime, MarketSnapshot

def detect_market_regime(
    nifty_snapshot: MarketSnapshot,
    adx: float,
    atr_percent: float,
    vix: float,
    advances: int,
    declines: int
) -> MarketRegime:
    
    # 1. Breadth
    total = max(1, advances + declines)
    adv_ratio = advances / total
    
    trend = nifty_snapshot.change_percent
    
    # Simple rule-based regime detection
    if vix > 25 or atr_percent > 2.5:
        regime = "VOLATILE"
        confidence = 90
    elif adx < 20:
        if abs(trend) < 0.5:
            regime = "RANGEBOUND"
            confidence = 85
        else:
            regime = "MEAN_REVERTING"
            confidence = 75
    elif adx >= 20:
        if trend > 0.5 and adv_ratio > 0.6:
            regime = "TRENDING_BULLISH"
            confidence = min(100, int(adx * 3))
        elif trend < -0.5 and adv_ratio < 0.4:
            regime = "TRENDING_BEARISH"
            confidence = min(100, int(adx * 3))
        else:
            regime = "VOLATILE"
            confidence = 60
    else:
        regime = "RANGEBOUND"
        confidence = 50
        
    return MarketRegime(
        regime=regime,
        confidence=confidence
    )
