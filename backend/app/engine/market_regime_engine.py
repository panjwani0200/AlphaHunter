from app.domain.contracts import MarketRegime, MarketSnapshot

class MarketRegimeEngine:
    def __init__(self) -> None:
        pass

    def detect_regime(
        self,
        nifty_snapshot: MarketSnapshot | None,
        banknifty_snapshot: MarketSnapshot | None,
        vix: float = 15.0,
        advances: int = 25,
        declines: int = 25,
        sector_breadth: float = 0.5,
        gap_pct: float = 0.0,
        days_to_major_event: int = 10
    ) -> MarketRegime:
        """
        Classify market into: TRENDING_BULL, TRENDING_BEAR, SIDEWAYS, HIGH_VOLATILITY, EVENT_DRIVEN.
        """
        total = max(1, advances + declines)
        adv_ratio = advances / total
        
        nifty_change = nifty_snapshot.change_percent if nifty_snapshot else 0.0
        banknifty_change = banknifty_snapshot.change_percent if banknifty_snapshot else 0.0
        
        # 1. High Volatility Check
        if vix > 22.0 or abs(gap_pct) > 1.2:
            return MarketRegime(
                regime="HIGH_VOLATILITY",
                confidence=int(round(min(100.0, float(vix * 3.5))))
            )
            
        # 2. Event Driven Check
        if days_to_major_event <= 1:
            return MarketRegime(
                regime="EVENT_DRIVEN",
                confidence=95
            )

        # 3. Trending Bullish
        if (nifty_change > 0.3 or banknifty_change > 0.4) and adv_ratio > 0.58 and sector_breadth > 0.6:
            # High confidence if both indices align
            confidence = 85 if nifty_change * banknifty_change > 0 else 70
            return MarketRegime(
                regime="TRENDING_BULL",
                confidence=confidence
            )

        # 4. Trending Bearish
        if (nifty_change < -0.3 or banknifty_change < -0.4) and adv_ratio < 0.42 and sector_breadth < 0.4:
            confidence = 85 if nifty_change * banknifty_change > 0 else 70
            return MarketRegime(
                regime="TRENDING_BEAR",
                confidence=confidence
            )

        # 5. Sideways
        # Default fallback is Sideways rangebound
        return MarketRegime(
            regime="SIDEWAYS",
            confidence=int(round(80.0 - abs(nifty_change) * 10))
        )

# Global Instance
market_regime_engine = MarketRegimeEngine()
