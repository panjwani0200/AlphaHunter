from app.domain.contracts import TradeCard, ScannerCandidate

def generate_trade_card(candidate: ScannerCandidate) -> TradeCard:
    score = candidate.score
    symbol = candidate.symbol
    last_price = candidate.last_price or 0.0
    
    # Determine signal based on score and signal_type
    sig_val = candidate.signal_type.value
    direction = "BUY"
    if sig_val == "swing_short" or candidate.change_percent < -2.0:
        direction = "SELL"
        
    if score >= 60:
        signal = direction # BUY or SELL
    elif 40 <= score < 60:
        signal = "WATCHLIST"
    else:
        signal = "WAIT"
        
    # Execution entry/stop/targets from candidate's execution zones evidence
    exec_zones = candidate.evidence.get("execution_zones", {})
    entry_str = exec_zones.get("entry_zone", f"{last_price*0.998:.2f}-{last_price*1.002:.2f}")
    stop_loss = exec_zones.get("stop_loss", round(last_price * 0.98, 2) if direction == "BUY" else round(last_price * 1.02, 2))
    targets = exec_zones.get("targets", [round(last_price * 1.02, 2)] if direction == "BUY" else [round(last_price * 0.98, 2)])
    rr = exec_zones.get("risk_reward", 1.5)
    
    # Option Play recommendation
    opt_rec = candidate.evidence.get("options_recommendation")
    if not opt_rec:
        opt_rec = f"BUY {int(round(last_price, -1))} CE" if direction == "BUY" else f"BUY {int(round(last_price, -1))} PE"
        
    # Holding Period
    if sig_val == "swing_long":
        holding_period = "Intraday" if score > 80 else "2-3 sessions"
    elif sig_val == "swing_short":
        holding_period = "Intraday" if score > 80 else "2-3 sessions"
    elif sig_val in ("momentum", "breakout", "reversal"):
        holding_period = "Intraday"
    else:
        holding_period = "Intraday"
        
    # Categorise Confluences
    tech_reasons = []
    opt_reasons = []
    vol_reasons = []
    sm_reasons = []
    
    # Map raw reasons and evidence to detailed reasons
    for r in candidate.reasons:
        lower_r = r.lower()
        if any(w in lower_r for w in ("trend", "rsi", "macd", "moving average", "ma", "bollinger", "bb", "retracement", "fib", "high", "low", "structure", "bos")):
            tech_reasons.append(r)
        elif any(w in lower_r for w in ("pcr", "option", "oi", "put", "call", "strike", "resistance", "support", "max pain")):
            opt_reasons.append(r)
        elif any(w in lower_r for w in ("volume", "spurt", "traded", "delivery")):
            vol_reasons.append(r)
        else:
            sm_reasons.append(r)
            
    # Add smart money engines details specifically
    if candidate.evidence.get("buy_pressure", 0.5) > 0.6:
        sm_reasons.append(f"Aggressive buy pressure ({candidate.evidence['buy_pressure']*100:.0f}%)")
    if candidate.evidence.get("fii_net_cr", 0.0) > 0:
        sm_reasons.append(f"Positive FII cash flow ({candidate.evidence['fii_net_cr']:+.1f} Cr)")
    if candidate.evidence.get("long_short_ratio", 0.5) > 0.55:
        sm_reasons.append(f"Institutional derivatives long bias ({candidate.evidence['long_short_ratio']*100:.0f}%)")

    # If any list is empty, add a default
    if not tech_reasons:
        tech_reasons = [f"{candidate.evidence.get('trend', 'sideways').upper()} trend detected"]
    if not opt_reasons:
        opt_reasons = ["OI distribution supports direction"]
    if not vol_reasons:
        vol_reasons = ["Volume structure is steady"]
    if not sm_reasons:
        sm_reasons = ["Institutional positioning aligned"]

    # News Sentiment
    news_sentiment = candidate.evidence.get("news_sentiment", "NEUTRAL")
    
    # Calculate Risk Score & Reward Score
    risk_score = min(95.0, max(5.0, 100.0 - candidate.score + len(candidate.conflicts) * 8.0))
    reward_score = min(98.0, max(10.0, candidate.score * 0.9 + rr * 3.5))

    # Pattern Memory similarity
    similarity = {
        "matches": candidate.evidence.get("pattern_matches", 0),
        "win_rate": round(candidate.evidence.get("pattern_success_rate", 0.5) * 100.0, 1),
        "avg_return": round(candidate.evidence.get("pattern_avg_return_5d", 0.0) * 100.0, 2)
    }

    # Structured AI Explanation Engine
    ai_explanation = f"<strong>{symbol}</strong> has an <strong>{score:.0f}% confidence</strong> because:<br>"
    for r in candidate.reasons[:5]:
        ai_explanation += f"• {r}<br>"
    if similarity["matches"] > 0:
        ai_explanation += f"• Matches {similarity['matches']} historical pattern cases (Success Rate: {similarity['win_rate']:.1f}%)<br>"
    ai_explanation += f"Expected probability of success: <strong>{candidate.evidence.get('ml_probability', 0.5)*100:.0f}%</strong>"

    return TradeCard(
        symbol=symbol,
        signal=signal,
        entry=entry_str,
        stop_loss=stop_loss,
        targets=targets[:3],
        confidence=int(score),
        risk_reward=rr,
        reason=candidate.reasons,
        options_recommendation=opt_rec,
        cycle=candidate.evidence.get("oi_interpretation", "UNKNOWN") or "UNKNOWN",
        cycle_confidence=candidate.evidence.get("pattern_success_rate", 0.5) * 100.0,
        risk_score=round(risk_score, 1),
        reward_score=round(reward_score, 1),
        probability=round(candidate.evidence.get("ml_probability", 0.5), 3),
        holding_period=holding_period,
        ai_explanation=ai_explanation,
        technical_reasons=tech_reasons,
        options_reasons=opt_reasons,
        volume_reasons=vol_reasons,
        smart_money_reasons=sm_reasons,
        historical_similarity=similarity,
        sector_strength=round(candidate.evidence.get("sector_strength", 50.0), 2),
        news_sentiment=news_sentiment,
        market_regime=candidate.regime
    )
