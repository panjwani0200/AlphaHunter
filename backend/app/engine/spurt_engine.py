from typing import Any

from app.domain.contracts import OiInterpretation


class SpurtEngine:
    def __init__(self):
        pass

    def evaluate_spurt(
        self,
        symbol: str,
        today_volume: int,
        avg_20d_volume: int,
        today_delivery: float,
        avg_30d_delivery: float,
        today_change_pct: float,
        oi_interpretation: OiInterpretation | None,
        near_breakout: bool,
    ) -> dict[str, Any]:
        """
        Evaluates Volume, Delivery, Price, and OI spurts to detect early momentum.
        """
        vol_spurt = round(today_volume / avg_20d_volume, 2) if avg_20d_volume else 0.0
        del_spurt = round(today_delivery - avg_30d_delivery, 2) if avg_30d_delivery else 0.0
        price_spurt = abs(today_change_pct)
        
        # oi_change_pct = 0.0 # Could be passed in, simplified here
        
        early_trade_alert = False
        probability = "LOW"
        
        if vol_spurt > 2.0 and del_spurt > 15.0 and near_breakout and today_change_pct > 0:
            early_trade_alert = True
            if oi_interpretation == OiInterpretation.LONG_BUILDUP:
                probability = "HIGH"
            elif oi_interpretation == OiInterpretation.SHORT_COVERING:
                probability = "MEDIUM"
                
        return {
            "early_trade_alert": early_trade_alert,
            "volume_spurt": vol_spurt,
            "delivery_spurt": del_spurt,
            "price_spurt": price_spurt,
            "probability": probability,
            "oi_interpretation": oi_interpretation.value if oi_interpretation else "N/A"
        }
