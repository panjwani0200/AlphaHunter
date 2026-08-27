from typing import Any
from app.domain.contracts import MarketSnapshot, OiSnapshot, OiInterpretation
from app.engine.trend_engine import analyze_trend
from app.engine.smc_engine import analyze_smc
from app.engine.fib_engine import analyze_fibonacci
from app.engine.session_engine import evaluate_session
from app.engine.news_engine import analyze_news_sentiment

def evaluate_signal_pro(
    snapshot: MarketSnapshot,
    oi_snapshot: OiSnapshot | None,
    regime_score: float = 50.0,
    sector_score: float = 50.0
) -> dict[str, Any]:
    # Run core engines
    trend_res = analyze_trend(snapshot.candles)
    smc_res = analyze_smc(snapshot.candles)
    fib_res = analyze_fibonacci(snapshot.candles)
    _ = evaluate_session(snapshot.observed_at)
    news_res = analyze_news_sentiment(snapshot.symbol, snapshot.observed_at)
    
    # Calculate Volume Score
    volume_ratio = snapshot.volume / snapshot.average_volume_20d if snapshot.average_volume_20d else 1.0
    _ = min(100, int(volume_ratio * 40))
    
    # Calculate OI Score
    oi_score = 50
    if oi_snapshot:
        if oi_snapshot.interpretation in (OiInterpretation.LONG_BUILDUP, OiInterpretation.SHORT_BUILDUP):
            oi_score = 90
        elif oi_snapshot.interpretation in (OiInterpretation.SHORT_COVERING, OiInterpretation.LONG_UNWINDING):
            oi_score = 75

    # Determine direction based on Trend and SMC (confluence required)
    direction = "WAIT"
    is_bullish = trend_res.trend == "BULLISH" and ("BULLISH" in smc_res.signal or smc_res.signal == "NEUTRAL")
    is_bearish = trend_res.trend == "BEARISH" and ("BEARISH" in smc_res.signal or smc_res.signal == "NEUTRAL")

    if is_bullish:
        direction = "BUY"
    elif is_bearish:
        direction = "SELL"
    else:
        # Fallback for UI demonstration: infer direction from trend
        if trend_res.trend == "BULLISH":
            direction = "BUY"
        elif trend_res.trend == "BEARISH":
            direction = "SELL"
        else:
            direction = "BUY" # Default to buy for neutral to allow score-based watchlist
        
    # We invert News/Fib/SMC scores if they disagree with the primary direction, 
    # but for simplicity, we assume the scores are absolute strength.
    # A true system would penalize opposing signals.
    if direction == "BUY" and news_res.news_sentiment == "BEARISH":
        news_res.score = 100 - news_res.score
    if direction == "SELL" and news_res.news_sentiment == "BULLISH":
        news_res.score = 100 - news_res.score
        
    # Apply weights using the new Market Structure Formula:
    # Trend*0.20 + SMC*0.15 + Fib*0.10 + OI*0.15 + News*0.10 + Regime*0.10 + Sector*0.10 + Cycle*0.10
    
    # Base Cycle score is initialized to 50 if neutral/unknown
    cycle_score = 50.0
    if snapshot.cycle_metrics:
        # We can map the probability modifier to a score out of 100
        # e.g., if mod is +15, it acts as a strong boost
        # Let's map it: a modifier of +15 is roughly equivalent to a 90/100 score in this category
        mod = snapshot.cycle_metrics.probability_modifier
        cycle_score = min(100.0, max(0.0, 50 + (mod * 2.5)))
        
    final_score = (
        trend_res.strength * 0.20 +
        smc_res.smc_score * 0.15 +
        fib_res.score * 0.10 +
        oi_score * 0.15 +
        news_res.score * 0.10 +
        regime_score * 0.10 +
        sector_score * 0.10 +
        cycle_score * 0.10
    )
    
    # We apply the actual raw cycle modifier to the final probability as requested
    if snapshot.cycle_metrics:
        final_score += snapshot.cycle_metrics.probability_modifier
        final_score = min(100.0, max(0.0, final_score))

    
    final_score_int = int(final_score)
    
    reasons = []
    if trend_res.trend != "NEUTRAL":
        reasons.append(f"{trend_res.trend.capitalize()} trend")
    if smc_res.signal != "NEUTRAL":
        reasons.append(f"SMC: {smc_res.signal.replace('_', ' ')}")
    if fib_res.confluence:
        reasons.append("Fib confluence")
    if oi_score >= 75 and oi_snapshot:
        reasons.append(oi_snapshot.interpretation.value.replace('_', ' ').capitalize())
    
    if snapshot.cycle_metrics:
        reasons.append(f"Cycle Phase: {snapshot.cycle_metrics.phase.value.upper()}")
        
    return {
        "symbol": snapshot.symbol,
        "direction": direction,
        "score": final_score_int,
        "reasons": reasons,
        "cycle": snapshot.cycle_metrics.phase.value.upper() if snapshot.cycle_metrics else "UNKNOWN",
        "cycle_confidence": snapshot.cycle_metrics.confidence if snapshot.cycle_metrics else 0.0
    }
