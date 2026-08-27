from __future__ import annotations

from app.domain.contracts import (
    MarketSnapshot,
    OiInterpretation,
    OiSnapshot,
    OptionChainAnalysis,
    ScannerCandidate,
    SignalType,
    TechnicalAnalysis,
    VolumeTrend,
)


def score_candidate(
    snapshot: MarketSnapshot,
    technicals: TechnicalAnalysis,
    oi_snapshot: OiSnapshot | None = None,
    option_chain: OptionChainAnalysis | None = None,
    sector_score: float = 50.0,
) -> ScannerCandidate:
    reasons: list[str] = []
    conflicts: list[str] = []

    # ── Price breakout quality (max 20) ─────────────────────────────────────
    price_breakout_score = min(20.0, max(0.0, technicals.breakout_quality / 5))
    if price_breakout_score >= 12:
        reasons.append("Price is pressing against recent resistance")

    # ── Volume surge (max 15) ────────────────────────────────────────────────
    volume_ratio = snapshot.volume / snapshot.average_volume_20d if snapshot.average_volume_20d else 1
    volume_score = min(15.0, max(0.0, (volume_ratio - 1) * 10))
    if volume_score >= 8:
        reasons.append(f"Volume is {volume_ratio:.1f}x the 20-day average")
    if technicals.volume_trend == VolumeTrend.RISING:
        volume_score = min(15.0, volume_score + 2.0)
        reasons.append("Volume trend is rising across recent sessions")
    elif technicals.volume_trend == VolumeTrend.FALLING and volume_score > 0:
        volume_score = max(0.0, volume_score - 2.0)
        conflicts.append("Short-term volume trend is fading")

    # ── Open interest (max 20) ───────────────────────────────────────────────
    oi_score = 0.0
    futures_premium_score = 5.0
    signal_type = SignalType.MOMENTUM
    if oi_snapshot:
        if oi_snapshot.interpretation == OiInterpretation.LONG_BUILDUP:
            oi_score = min(20.0, 12 + max(0.0, oi_snapshot.oi_change_percent))
            signal_type = SignalType.BREAKOUT
            reasons.append("Futures OI confirms long build-up")
        elif oi_snapshot.interpretation == OiInterpretation.SHORT_BUILDUP:
            oi_score = min(20.0, 12 + abs(min(0.0, oi_snapshot.price_change_percent)))
            signal_type = SignalType.SWING_SHORT
            reasons.append("OI points to short build-up")
        elif oi_snapshot.interpretation == OiInterpretation.SHORT_COVERING:
            oi_score = 10.0
            reasons.append("Short covering supports the move")
        elif oi_snapshot.interpretation == OiInterpretation.LONG_UNWINDING:
            conflicts.append("OI shows long unwinding")

    # ── RSI (max 10) ─────────────────────────────────────────────────────────
    rsi_score = 0.0
    if technicals.rsi_14 is not None:
        if 50 <= technicals.rsi_14 <= 68:
            rsi_score = 10.0
            reasons.append("RSI is bullish without being overheated")
        elif technicals.rsi_14 > 78:
            rsi_score = 2.0
            conflicts.append("RSI is overheated")
        elif technicals.rsi_14 < 40:
            rsi_score = 1.0
            conflicts.append("RSI is weak")

    # ── Option chain (max 15) ─────────────────────────────────────────────────
    option_chain_score = 0.0
    if option_chain:
        if option_chain.support and snapshot.last_price >= option_chain.support:
            option_chain_score += 8.0
            reasons.append("Put OI support is below current price")
        if option_chain.resistance and snapshot.last_price > option_chain.resistance:
            option_chain_score += 7.0
            reasons.append("Price has cleared option-chain resistance")
        elif option_chain.resistance and snapshot.last_price < option_chain.resistance:
            conflicts.append("Option-chain resistance is still overhead")
    option_chain_score = min(15.0, option_chain_score)

    # ── Sector strength (max 10) ──────────────────────────────────────────────
    sector_strength_score = min(10.0, max(0.0, sector_score / 10))
    if sector_strength_score >= 7:
        reasons.append("Sector strength is supportive")
    elif sector_strength_score <= 3:
        conflicts.append("Sector trend is weak")

    # ── MACD crossover (max 5) ────────────────────────────────────────────────
    macd_score = 0.0
    if technicals.macd is not None and technicals.macd_signal is not None:
        if technicals.macd > technicals.macd_signal and technicals.macd_histogram and technicals.macd_histogram > 0:
            macd_score = 5.0
            reasons.append("MACD is above signal line with positive histogram")
        elif technicals.macd < technicals.macd_signal:
            macd_score = 0.0
            conflicts.append("MACD is below signal line — bearish crossover")

    # ── Bollinger Band breakout (max 5) ────────────────────────────────────────
    bb_score = 0.0
    if technicals.bb_upper and technicals.bb_lower and technicals.bb_width is not None:
        if snapshot.last_price >= technicals.bb_upper:
            bb_score = 5.0
            reasons.append("Price has broken above the upper Bollinger Band")
        elif technicals.bb_width < 3.0:
            bb_score = 3.0
            reasons.append("Bollinger Band squeeze signals potential breakout setup")
        elif snapshot.last_price <= technicals.bb_lower:
            conflicts.append("Price is below lower Bollinger Band — oversold or breakdown")

    # ── 52-week high proximity (max 5) ────────────────────────────────────────
    proximity_score = 0.0
    if technicals.week52_high:
        proximity_pct = ((snapshot.last_price - technicals.week52_high) / technicals.week52_high) * 100
        if proximity_pct >= 0:
            proximity_score = 5.0
            reasons.append("Price is at or above the 52-week high")
        elif proximity_pct >= -3:
            proximity_score = 4.0
            reasons.append("Price is within 3% of 52-week high")
        elif proximity_pct >= -8:
            proximity_score = 2.0
        elif proximity_pct < -25:
            conflicts.append("Price is more than 25% off 52-week high")

    # ── Signal type refinement ────────────────────────────────────────────────
    if technicals.trend == "up" and signal_type == SignalType.MOMENTUM:
        signal_type = SignalType.SWING_LONG
    if technicals.trend == "down" and snapshot.change_percent < -2:
        signal_type = SignalType.REVERSAL
    if macd_score >= 5 and price_breakout_score >= 12 and signal_type != SignalType.SWING_SHORT:
        signal_type = SignalType.BREAKOUT

    # Calculate ATR expansion, VWAP distance, and gap pct for XGBoost feature inputs
    closes = [c.close for c in snapshot.candles] if snapshot.candles else [snapshot.last_price]
    highs = [c.high for c in snapshot.candles] if snapshot.candles else [snapshot.last_price]
    lows = [c.low for c in snapshot.candles] if snapshot.candles else [snapshot.last_price]
    
    if len(snapshot.candles) >= 14:
        tr = [max(h - lo, abs(h - pc), abs(lo - pc)) for h, lo, pc in zip(highs[-14:], lows[-14:], closes[-15:-1])]
        atr = sum(tr) / 14
        tr_all = [max(h - lo, abs(h - pc), abs(lo - pc)) for h, lo, pc in zip(highs, lows, closes[:-1] or [closes[0]])]
        atr_all = sum(tr_all) / len(tr_all) if tr_all else atr
        atr_expansion = atr / (atr_all or 1.0)
    else:
        atr = snapshot.last_price * 0.015
        atr_expansion = 1.0
        
    if snapshot.candles:
        tp = [(c.high + c.low + c.close) / 3.0 for c in snapshot.candles[-20:]]
        vols = [c.volume for c in snapshot.candles[-20:]]
        vwap = sum(t * v for t, v in zip(tp, vols)) / sum(vols) if sum(vols) > 0 else snapshot.last_price
        vwap_dist = (snapshot.last_price - vwap) / vwap
    else:
        vwap_dist = 0.0
        
    if len(snapshot.candles) >= 2:
        gap_pct = ((snapshot.candles[-1].open - snapshot.candles[-2].close) / snapshot.candles[-2].close) * 100.0
    else:
        gap_pct = 0.0

    # ── ML Model Probability Prediction using XGBoost ─────────────────────────
    from app.engine.ml_model import ml_scoring_model
    prob = ml_scoring_model.predict_probability(
        volume_ratio=volume_ratio,
        change_percent=snapshot.change_percent,
        last_price=snapshot.last_price,
        week52_high=technicals.week52_high,
        atr_expansion=atr_expansion,
        vwap_dist=vwap_dist,
        gap_pct=gap_pct,
        delivery_ratio=snapshot.delivery_percent or 0.35,
        pcr=option_chain.pcr if option_chain else 0.9,
        max_pain_dist=0.0, # fallback
        sector_strength=sector_score
    )
    ml_score = prob * 100.0
    
    if prob >= 0.65:
        reasons.append(f"XGBoost Model predicts {prob*100:.0f}% probability of short-term breakout")
    elif prob <= 0.35:
        conflicts.append(f"XGBoost Model warns of low breakout probability ({prob*100:.0f}%)")

    # ── Invoke Institutional Engines ──
    # 1. Market Regime
    from app.engine.market_regime_engine import market_regime_engine
    regime_res = market_regime_engine.detect_regime(
        nifty_snapshot=None,
        banknifty_snapshot=None,
        sector_breadth=sector_score / 100.0,
        gap_pct=gap_pct
    )
    regime = regime_res.regime
    reasons.append(f"Current Market Regime: {regime} (Confidence: {regime_res.confidence:.0f}%)")
    
    # 2. Pattern Memory
    from app.engine.pattern_memory_engine import PatternMemoryEngine
    pattern_memory = PatternMemoryEngine()
    pattern_res = pattern_memory.find_similar_setups(snapshot.candles)
    pattern_reliability = pattern_res["win_rate"]
    if pattern_res["matches_found"] > 0:
        reasons.append(f"Historical Similar Setups: {pattern_res['matches_found']} (Success Rate: {pattern_reliability*100:.0f}%)")
        
    # 3. Order Flow
    from app.engine.order_flow_engine import order_flow_engine
    flow_res = order_flow_engine.evaluate_order_flow(
        last_price=snapshot.last_price,
        high=max(highs[-20:]) if highs else snapshot.last_price,
        low=min(lows[-20:]) if lows else snapshot.last_price,
        volume=snapshot.volume,
        avg_volume_20d=snapshot.average_volume_20d or 1.0
    )
    buy_pressure = flow_res["buy_pressure"]
    
    # 4. Institutional Flow
    from app.engine.institutional_flow_engine import institutional_flow_engine
    inst_res = institutional_flow_engine.evaluate_flows(snapshot.symbol)
    
    # 4b. News Sentiment & Stealth Setup Detection
    from app.engine.news_engine import analyze_news_sentiment
    news_res = analyze_news_sentiment(snapshot.symbol, snapshot.observed_at)
    
    is_stealth_setup = False
    if news_res.news_sentiment == "NEUTRAL":
        has_volume_spurt = volume_ratio > 1.2
        has_buy_pressure = buy_pressure > 0.58
        has_long_buildup = oi_snapshot and oi_snapshot.interpretation == OiInterpretation.LONG_BUILDUP
        has_high_delivery = snapshot.delivery_percent is not None and snapshot.delivery_percent >= 0.40
        
        if has_volume_spurt or has_buy_pressure or has_long_buildup or has_high_delivery:
            is_stealth_setup = True
            reasons.append("Stealth Institutional Buildup (Zero public news buzz)")
            if has_volume_spurt and has_high_delivery:
                reasons.append("Quiet accumulation: High delivery / low public news focus")
    
    # 5. Multi-Timeframe Alignment
    from app.engine.multi_timeframe_engine import multi_timeframe_engine
    mtf_res = multi_timeframe_engine.evaluate_alignment(snapshot.symbol, snapshot.candles)
    if mtf_res["all_aligned"]:
        reasons.append("Multi-timeframe (Daily/1H/15m) aligned bullish")
    else:
        conflicts.append("Multi-timeframe mismatch")
        
    # 6. Execution Zones
    from app.engine.execution_engine import execution_engine
    exec_res = execution_engine.evaluate_entry(
        close_price=snapshot.last_price,
        prev_close=snapshot.previous_close,
        ema_9=snapshot.last_price, 
        prev_ema_9=snapshot.previous_close,
        volume=snapshot.volume,
        avg_volume=snapshot.average_volume_20d or 1,
        atr=atr
    )
    risk_reward = exec_res["execution_zones"]["risk_reward"]

    # ── Normalize components to 0-100 scores ──
    trend_score = min(100.0, max(0.0, (macd_score * 10) + (rsi_score * 5)))
    options_score = min(100.0, max(0.0, (option_chain_score * 6.66)))
    cycle_score = (snapshot.cycle_metrics.probability_modifier * 10.0 + 50.0) if snapshot.cycle_metrics else sector_score
    pattern_memory_score = pattern_reliability * 100.0
    delivery_score = (snapshot.delivery_percent * 100.0) if snapshot.delivery_percent is not None else 50.0
    
    # Fibonacci levels proximity calculation
    if len(snapshot.candles) >= 60:
        swing_high = max(c.high for c in snapshot.candles[-60:])
        swing_low = min(c.low for c in snapshot.candles[-60:])
    else:
        swing_high = snapshot.last_price * 1.10
        swing_low = snapshot.last_price * 0.90
    diff = swing_high - swing_low
    fibs = [swing_high - 0.382 * diff, swing_high - 0.5 * diff, swing_high - 0.618 * diff]
    closest_fib_dist = min(abs(snapshot.last_price - val) / snapshot.last_price for val in fibs)
    fib_score = max(0.0, min(100.0, 100.0 - (closest_fib_dist * 500.0)))
    
    spurt_score = min(100.0, max(0.0, (volume_ratio * 15.0) + (delivery_score * 0.3) + (snapshot.change_percent * 5.0)))
    structure_score = min(100.0, max(0.0, proximity_score * 20))
    execution_score = 100.0 if mtf_res["min15_trigger"] == "BUY_CONFIRMED" else 50.0

    # ── Dynamic Regime Weights ──
    if regime == "TRENDING_BULL":
        weights = {
            "ml": 0.15, "trend": 0.20, "options": 0.05, "cycle": 0.03, "pattern": 0.05,
            "delivery": 0.10, "fib": 0.02, "spurt": 0.15, "structure": 0.15, "execution": 0.10
        }
    elif regime == "TRENDING_BEAR":
        weights = {
            "ml": 0.15, "trend": 0.20, "options": 0.15, "cycle": 0.05, "pattern": 0.05,
            "delivery": 0.05, "fib": 0.05, "spurt": 0.05, "structure": 0.10, "execution": 0.15
        }
    elif regime == "SIDEWAYS":
        weights = {
            "ml": 0.10, "trend": 0.05, "options": 0.25, "cycle": 0.20, "pattern": 0.03,
            "delivery": 0.05, "fib": 0.15, "spurt": 0.05, "structure": 0.02, "execution": 0.10
        }
    elif regime == "HIGH_VOLATILITY":
        weights = {
            "ml": 0.20, "trend": 0.15, "options": 0.10, "cycle": 0.03, "pattern": 0.10,
            "delivery": 0.05, "fib": 0.02, "spurt": 0.05, "structure": 0.05, "execution": 0.25
        }
    else:  # EVENT_DRIVEN
        weights = {
            "ml": 0.15, "trend": 0.10, "options": 0.20, "cycle": 0.03, "pattern": 0.10,
            "delivery": 0.05, "fib": 0.02, "spurt": 0.05, "structure": 0.05, "execution": 0.25
        }

    weighted_blend = (
        ml_score * weights["ml"] +
        trend_score * weights["trend"] +
        options_score * weights["options"] +
        cycle_score * weights["cycle"] +
        pattern_memory_score * weights["pattern"] +
        delivery_score * weights["delivery"] +
        fib_score * weights["fib"] +
        spurt_score * weights["spurt"] +
        structure_score * weights["structure"] +
        execution_score * weights["execution"]
    )

    # ── Dynamic Multiplier Normalisation ──
    # Alpha Score = (weighted_blend * 0.4) + (weighted_blend * 0.6 * Multiplier)
    confidence_mult = (sector_score / 50.0) * (1.2 if mtf_res["all_aligned"] else 0.8)
    regime_mult = 1.2 if regime == "TRENDING_BULL" else 0.7 if regime == "TRENDING_BEAR" else 1.0
    
    # Calculate product multiplier
    multiplier = prob * (risk_reward / 2.0) * confidence_mult * regime_mult * pattern_reliability
    # Bound multiplier to safe range to prevent score compression
    multiplier = max(0.2, min(1.8, multiplier))
    
    final_score = (weighted_blend * 0.40) + (weighted_blend * 0.60 * multiplier)
    if is_stealth_setup:
        # Boost stealth opportunities to surface them in Signal Center
        final_score += 15.0
        
    final_score = round(max(0.0, min(100.0, final_score)), 2)

    # ── Signal Tier Classification ──
    if final_score >= 90.0:
        signal_tier = "S"
    elif final_score >= 80.0:
        signal_tier = "A"
    elif final_score >= 70.0:
        signal_tier = "B"
    elif final_score >= 60.0:
        signal_tier = "C"
    else:
        signal_tier = "Ignore"

    return ScannerCandidate(
        symbol=snapshot.symbol,
        signal_type=signal_type,
        score=final_score,
        price_breakout_score=round(price_breakout_score, 2),
        oi_score=round(oi_score, 2),
        volume_score=round(volume_score, 2),
        futures_premium_score=round(futures_premium_score, 2),
        rsi_score=round(rsi_score, 2),
        option_chain_score=round(option_chain_score, 2),
        sector_strength_score=round(sector_strength_score, 2),
        macd_score=round(macd_score, 2),
        bb_score=round(bb_score, 2),
        proximity_score=round(proximity_score, 2),
        # Institutional Scores
        ml_score=round(ml_score, 2),
        trend_score=round(trend_score, 2),
        options_score=round(options_score, 2),
        cycle_score=round(cycle_score, 2),
        pattern_memory_score=round(pattern_memory_score, 2),
        delivery_score=round(delivery_score, 2),
        fib_score=round(fib_score, 2),
        spurt_score=round(spurt_score, 2),
        structure_score=round(structure_score, 2),
        execution_score=round(execution_score, 2),
        
        signal_tier=signal_tier,
        regime=regime,
        last_price=snapshot.last_price,
        change_percent=snapshot.change_percent,
        candles=snapshot.candles,
        reasons=reasons,
        conflicts=conflicts,
        evidence={
            "sector": snapshot.sector,
            "last_price": snapshot.last_price,
            "previous_close": snapshot.previous_close,
            "change_percent": snapshot.change_percent,
            "volume": snapshot.volume,
            "average_volume_20d": snapshot.average_volume_20d,
            "delivery_percent": snapshot.delivery_percent,
            "volume_ratio": round(volume_ratio, 2),
            "trend": technicals.trend,
            "rsi_14": technicals.rsi_14,
            "macd": technicals.macd,
            "macd_signal": technicals.macd_signal,
            "macd_histogram": technicals.macd_histogram,
            "adx": technicals.adx,
            "bb_upper": technicals.bb_upper,
            "bb_lower": technicals.bb_lower,
            "bb_width": technicals.bb_width,
            "week52_high": technicals.week52_high,
            "week52_low": technicals.week52_low,
            "volume_trend": technicals.volume_trend.value if technicals.volume_trend else None,
            "breakout_quality": technicals.breakout_quality,
            "support": technicals.support,
            "resistance": technicals.resistance,
            "oi_change_percent": oi_snapshot.oi_change_percent if oi_snapshot else None,
            "oi_interpretation": oi_snapshot.interpretation.value if oi_snapshot else None,
            "open_interest": oi_snapshot.open_interest if oi_snapshot else None,
            "pcr": option_chain.pcr if option_chain else None,
            "option_support": option_chain.support if option_chain else None,
            "option_resistance": option_chain.resistance if option_chain else None,
            "ml_probability": round(prob, 4),
            "ml_confidence": "high" if prob >= 0.70 or prob <= 0.30 else "medium",
            "news_sentiment": news_res.news_sentiment,
            
            # New Institutional outputs for UI cards
            "pattern_matches": pattern_res["matches_found"],
            "pattern_success_rate": pattern_reliability,
            "pattern_avg_return_5d": pattern_res["avg_return_5d"],
            "pattern_max_drawdown": pattern_res["max_drawdown"],
            "regime_confidence": regime_res.confidence,
            "buy_pressure": buy_pressure,
            "fii_net_cr": inst_res["fii_net_cr"],
            "dii_net_cr": inst_res["dii_net_cr"],
            "long_short_ratio": inst_res["derivatives_long_ratio"],
            "execution_zones": exec_res["execution_zones"]
        },
    )
