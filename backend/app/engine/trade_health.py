from __future__ import annotations

from app.domain.contracts import AlertAction, PositionState, ReversalAssessment, TradeHealth


def score_trade_health(position: PositionState, reversal: ReversalAssessment) -> TradeHealth:
    pnl_component = 0.0
    if position.pnl_percent is not None:
        pnl_component = max(-15.0, min(15.0, position.pnl_percent * 1.5))

    stop_component = 0.0
    if position.stop_loss and position.latest_price:
        distance_to_stop = ((position.latest_price - position.stop_loss) / position.latest_price) * 100
        stop_component = max(-20.0, min(20.0, distance_to_stop))

    score = 85 + pnl_component + stop_component - (reversal.score * 0.6)
    score = round(max(0.0, min(100.0, score)), 2)

    if score >= 85:
        action = AlertAction.HOLD
    elif score >= 70:
        action = AlertAction.HOLD
    elif score >= 55:
        action = AlertAction.WATCH
    elif score >= 40:
        action = AlertAction.REDUCE
    else:
        action = AlertAction.EXIT

    reasons = [f"Reversal risk score is {reversal.score:.0f}"]
    if position.pnl_percent is not None:
        reasons.append(f"Position PnL is {position.pnl_percent:.2f}%")
    reasons.extend(reversal.reasons[:2])

    return TradeHealth(symbol=position.symbol, score=score, action=action, reasons=reasons)

