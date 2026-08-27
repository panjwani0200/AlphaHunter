from __future__ import annotations

from app.domain.contracts import (
    AlertAction,
    MarketSnapshot,
    OiInterpretation,
    OiSnapshot,
    OptionChainAnalysis,
    PositionState,
    ReversalAssessment,
    TechnicalAnalysis,
)


def classify_reversal_action(score: float) -> AlertAction:
    if score >= 75:
        return AlertAction.EXIT
    if score >= 55:
        return AlertAction.REDUCE
    if score >= 30:
        return AlertAction.WATCH
    return AlertAction.HOLD


def assess_reversal(
    position: PositionState,
    snapshot: MarketSnapshot,
    technicals: TechnicalAnalysis,
    oi_snapshot: OiSnapshot | None = None,
    option_chain: OptionChainAnalysis | None = None,
    sector_score: float = 50.0,
) -> ReversalAssessment:
    score = 0.0
    reasons: list[str] = []
    evidence: dict[str, float | str | None] = {}

    support = technicals.support or position.stop_loss
    if support and snapshot.last_price < support:
        score += 30
        reasons.append(f"Support {support:.2f} is broken")
    evidence["support"] = support

    if oi_snapshot and oi_snapshot.interpretation == OiInterpretation.SHORT_BUILDUP:
        score += 25
        reasons.append("Short build-up is visible in OI")
    elif oi_snapshot and oi_snapshot.interpretation == OiInterpretation.LONG_UNWINDING:
        score += 18
        reasons.append("Long unwinding is visible in OI")

    if option_chain and option_chain.support and snapshot.last_price < option_chain.support:
        score += 20
        reasons.append("Put support has shifted above price")
    evidence["option_support"] = option_chain.support if option_chain else None

    if technicals.rsi_14 is not None and technicals.rsi_14 < 45:
        score += 10
        reasons.append("RSI shows weakening momentum")
    evidence["rsi_14"] = technicals.rsi_14

    if sector_score < 40:
        score += 10
        reasons.append("Sector backdrop is weak")
    evidence["sector_score"] = sector_score

    volume_ratio = snapshot.volume / snapshot.average_volume_20d if snapshot.average_volume_20d else 1.0
    if snapshot.change_percent < -1 and volume_ratio > 1.5:
        score += 5
        reasons.append("Price is falling on elevated volume")
    evidence["volume_ratio"] = round(volume_ratio, 2)

    score = min(100.0, score)
    action = classify_reversal_action(score)
    if not reasons:
        reasons.append("No major reversal confirmation")

    return ReversalAssessment(
        symbol=position.symbol,
        score=round(score, 2),
        action=action,
        reasons=reasons,
        evidence=evidence,
    )

