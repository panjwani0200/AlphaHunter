from app.domain.contracts import PositionState, MarketSnapshot, OiSnapshot, ExitSignal, OiInterpretation

def evaluate_exit(
    position: PositionState, 
    snapshot: MarketSnapshot, 
    oi_snapshot: OiSnapshot | None, 
    regime: str, 
    news_sentiment: str
) -> ExitSignal:
    current_price = snapshot.last_price
    
    # 1. Stop loss hit
    if position.stop_loss:
        if position.side == "long" and current_price <= position.stop_loss:
            return ExitSignal(symbol=position.symbol, action="FULL EXIT", reason="Stop loss hit")
        if position.side == "short" and current_price >= position.stop_loss:
            return ExitSignal(symbol=position.symbol, action="FULL EXIT", reason="Stop loss hit")
            
    # 2. Target hit
    if position.target_price:
        if position.side == "long" and current_price >= position.target_price:
            return ExitSignal(symbol=position.symbol, action="PARTIAL BOOK", reason="Target hit")
        if position.side == "short" and current_price <= position.target_price:
            return ExitSignal(symbol=position.symbol, action="PARTIAL BOOK", reason="Target hit")
            
    # 3. Long buildup lost / Short buildup lost
    if oi_snapshot:
        if position.side == "long" and oi_snapshot.interpretation in (OiInterpretation.LONG_UNWINDING, OiInterpretation.SHORT_BUILDUP):
            return ExitSignal(symbol=position.symbol, action="FULL EXIT", reason="Long buildup lost (OI Reversal)")
        if position.side == "short" and oi_snapshot.interpretation in (OiInterpretation.SHORT_COVERING, OiInterpretation.LONG_BUILDUP):
            return ExitSignal(symbol=position.symbol, action="FULL EXIT", reason="Short buildup lost (OI Reversal)")
            
    # 4. Market regime changed against position
    if position.side == "long" and "BEARISH" in regime:
        return ExitSignal(symbol=position.symbol, action="FULL EXIT", reason="Market regime turned Bearish")
    if position.side == "short" and "BULLISH" in regime:
        return ExitSignal(symbol=position.symbol, action="FULL EXIT", reason="Market regime turned Bullish")
        
    # 5. Major news reversal
    if position.side == "long" and news_sentiment == "BEARISH":
        return ExitSignal(symbol=position.symbol, action="FULL EXIT", reason="Major bearish news detected")
    if position.side == "short" and news_sentiment == "BULLISH":
        return ExitSignal(symbol=position.symbol, action="FULL EXIT", reason="Major bullish news detected")
        
    return ExitSignal(symbol=position.symbol, action="HOLD", reason="All parameters normal")
