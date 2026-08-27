from app.domain.contracts import PositionHealth, MarketSnapshot, OiSnapshot, OptionChainAnalysis

def evaluate_position_health(
    symbol: str,
    instrument: str | None,
    entry_price: float,
    current_price: float,
    snapshot: MarketSnapshot,
    oi_snapshot: OiSnapshot | None,
    option_chain: OptionChainAnalysis | None,
    sector_score: int
) -> PositionHealth:
    
    pnl = current_price - entry_price

    # Component Scores
    trend_score = 0     # Max 25
    oi_score = 0        # Max 20
    sect_score = 0      # Max 15
    opt_score = 0       # Max 20
    vol_score = 0       # Max 20

    # Trend Strength (25)
    if snapshot.change_percent > 1.5:
        trend_score = 25
    elif snapshot.change_percent > 0:
        trend_score = 15
    elif snapshot.change_percent > -1.0:
        trend_score = 5

    # OI Strength (20)
    if oi_snapshot:
        if oi_snapshot.interpretation == "long_buildup":
            oi_score = 20
        elif oi_snapshot.interpretation == "short_covering":
            oi_score = 15
        elif oi_snapshot.interpretation == "neutral":
            oi_score = 10
        elif oi_snapshot.interpretation == "long_unwinding":
            oi_score = 5

    # Sector Strength (15)
    sect_score = int((sector_score / 100) * 15)

    # Option Structure (20)
    if option_chain:
        if option_chain.pcr > 1.2:
            opt_score = 20
        elif option_chain.pcr > 0.8:
            opt_score = 10
        else:
            opt_score = 0

    # Volatility Structure (20)
    # Assume favorable if volume expands
    vol_ratio = snapshot.volume / max(1, snapshot.average_volume_20d)
    if vol_ratio > 1.5:
        vol_score = 20
    elif vol_ratio > 1.0:
        vol_score = 10
    else:
        vol_score = 5

    health_score = trend_score + oi_score + sect_score + opt_score + vol_score
    health_score = max(0, min(100, health_score))

    if health_score < 60:
        reversal_risk = "HIGH"
    elif health_score < 75:
        reversal_risk = "MEDIUM"
    else:
        reversal_risk = "LOW"

    return PositionHealth(
        symbol=symbol,
        instrument=instrument,
        entry_price=entry_price,
        current_price=current_price,
        pnl=pnl,
        health_score=health_score,
        reversal_risk=reversal_risk
    )
