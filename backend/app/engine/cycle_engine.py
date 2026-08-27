from app.domain.contracts import MarketSnapshot, TechnicalAnalysis, OiSnapshot, OiInterpretation, CyclePhase, CycleMetrics
import logging

logger = logging.getLogger(__name__)

def detect_cycle_phase(
    snapshot: MarketSnapshot,
    technicals: TechnicalAnalysis,
    oi_snapshot: OiSnapshot | None = None
) -> CycleMetrics:
    """
    Detect the institutional market cycle phase of a stock.
    Returns the phase, confidence score, and probability modifier.
    """
    # Base defaults
    phase = CyclePhase.ACCUMULATION
    confidence = 50.0
    probability_modifier = 0

    try:
        last_price = snapshot.last_price
        
        # 1. Price Structure & Trend
        trend = technicals.trend
        is_above_ema = technicals.ema_20 is not None and last_price > technicals.ema_20
        is_below_ema = technicals.ema_20 is not None and last_price < technicals.ema_20
        
        # 2. Volatility & Breakout
        is_breakout = technicals.breakout_quality >= 8.0
        
        # 3. RSI
        rsi = technicals.rsi_14 or 50.0
        
        # 4. Delivery & Volume
        delivery = snapshot.delivery_percent or 0.0
        is_strong_delivery = delivery > 50.0
        volume_ratio = snapshot.volume / snapshot.average_volume_20d if snapshot.average_volume_20d else 1.0
        
        # 5. OI Context
        oi_interp = oi_snapshot.interpretation if oi_snapshot else OiInterpretation.NEUTRAL

        # Scoring heuristics for each phase
        scores = {
            CyclePhase.ACCUMULATION: 0.0,
            CyclePhase.MARKUP: 0.0,
            CyclePhase.DISTRIBUTION: 0.0,
            CyclePhase.MARKDOWN: 0.0
        }

        # --- ACCUMULATION DETECTION ---
        # Price moving sideways for 10–30 sessions, Volatility compressed, ATR low
        if trend == "neutral" or (technicals.bb_width and technicals.bb_width < 5.0):
            scores[CyclePhase.ACCUMULATION] += 30
        if is_strong_delivery:
            scores[CyclePhase.ACCUMULATION] += 20
        if 40 <= rsi <= 60:
            scores[CyclePhase.ACCUMULATION] += 15
        if oi_interp in (OiInterpretation.NEUTRAL, OiInterpretation.LONG_BUILDUP):
            scores[CyclePhase.ACCUMULATION] += 15
        if not is_breakout:
            scores[CyclePhase.ACCUMULATION] += 10
            
        # --- MARKUP DETECTION ---
        # Resistance breakout, Higher highs, Volume spike, Strong delivery, OI rising, Price above VWAP
        if trend == "up":
            scores[CyclePhase.MARKUP] += 30
        if is_breakout:
            scores[CyclePhase.MARKUP] += 20
        if volume_ratio > 1.2:
            scores[CyclePhase.MARKUP] += 15
        if oi_interp == OiInterpretation.LONG_BUILDUP:
            scores[CyclePhase.MARKUP] += 20
        if is_above_ema:
            scores[CyclePhase.MARKUP] += 15
            
        # --- DISTRIBUTION DETECTION ---
        # Price near highs but momentum slowing, RSI bearish divergence, Call writing, Failed breakout
        if rsi > 70:
            scores[CyclePhase.DISTRIBUTION] += 20
        if trend == "up" and not is_breakout and volume_ratio < 0.8:
            scores[CyclePhase.DISTRIBUTION] += 25
        if oi_interp == OiInterpretation.SHORT_BUILDUP:
            scores[CyclePhase.DISTRIBUTION] += 25
        if is_below_ema and trend == "up":
            scores[CyclePhase.DISTRIBUTION] += 15
            
        # --- MARKDOWN DETECTION ---
        # Support breakdown, Lower highs, Short buildup, Volume selling spike, Price below VWAP
        if trend == "down":
            scores[CyclePhase.MARKDOWN] += 30
        if oi_interp in (OiInterpretation.SHORT_BUILDUP, OiInterpretation.LONG_UNWINDING):
            scores[CyclePhase.MARKDOWN] += 25
        if is_below_ema:
            scores[CyclePhase.MARKDOWN] += 20
        if volume_ratio > 1.2 and trend == "down":
            scores[CyclePhase.MARKDOWN] += 15
        if rsi < 40:
            scores[CyclePhase.MARKDOWN] += 10

        # Determine highest scoring phase
        best_phase = max(scores.items(), key=lambda x: x[1])
        phase = best_phase[0]
        # Normalize confidence to 50-99 range based on score strength
        base_confidence = min(99.0, max(50.0, best_phase[1]))
        confidence = round(base_confidence, 1)

        # Assign Probability Modifiers based on phase
        if phase == CyclePhase.ACCUMULATION:
            probability_modifier = 10  # +8 to +12
        elif phase == CyclePhase.MARKUP:
            probability_modifier = 15  # +12 to +18
        elif phase == CyclePhase.DISTRIBUTION:
            probability_modifier = -15 # -10 to -20
        elif phase == CyclePhase.MARKDOWN:
            probability_modifier = -20 # -15 to -25

    except Exception as e:
        logger.error(f"Error detecting cycle phase for {snapshot.symbol}: {e}")
        
    return CycleMetrics(
        phase=phase,
        confidence=confidence,
        probability_modifier=probability_modifier
    )
