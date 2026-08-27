from app.domain.contracts import ThesisValidationResult, MarketSnapshot, OiSnapshot, OptionChainAnalysis

def evaluate_thesis(
    symbol: str,
    entry_price: float,
    entry_thesis: dict,
    snapshot: MarketSnapshot,
    oi_snapshot: OiSnapshot | None,
    option_chain: OptionChainAnalysis | None,
    sector_score: int
) -> ThesisValidationResult:
    """
    Continuously evaluate whether the original trade thesis is still valid.
    """
    reasons = []
    confidence = 100
    status = "VALID"
    action = "HOLD"
    
    current_price = snapshot.last_price
    
    # 1. Price vs Support Check
    if "support" in entry_thesis:
        support_level = float(entry_thesis.get("support", 0.0))
        if current_price < support_level:
            reasons.append(f"Price ({current_price}) broke key support ({support_level})")
            confidence -= 30
            status = "WEAKENING"
            
    # 2. OI Trend Check
    if oi_snapshot:
        if oi_snapshot.interpretation == "long_unwinding":
            reasons.append("OI dropping sharply (Long Unwinding detected)")
            confidence -= 20
            if status == "VALID":
                status = "WEAKENING"
                
    # 3. Option Chain Shifts
    if option_chain:
        if option_chain.max_call_oi_strike and abs(option_chain.max_call_oi_strike - current_price) < (current_price * 0.01):
            reasons.append(f"Heavy call writing near spot at {option_chain.max_call_oi_strike}")
            confidence -= 15
            
        if option_chain.max_put_oi_strike and "entry_put_support" in entry_thesis:
            entry_ps = float(entry_thesis["entry_put_support"])
            if option_chain.max_put_oi_strike < entry_ps:
                reasons.append(f"Put support shifted lower from {entry_ps} to {option_chain.max_put_oi_strike}")
                confidence -= 25
                status = "WEAKENING"
                
    # 4. Sector Momentum Check
    if sector_score < 40:
        reasons.append(f"Sector momentum weakened (Score: {sector_score}/100)")
        confidence -= 15
        
    # Finalize status & action
    if confidence < 50:
        status = "BROKEN"
        action = "EXIT"
    elif confidence < 75:
        status = "WEAKENING"
        action = "REDUCE"
    else:
        status = "VALID"
        action = "HOLD"
        
    return ThesisValidationResult(
        status=status,
        confidence=max(0, min(100, confidence)),
        reasons=reasons,
        action=action
    )
