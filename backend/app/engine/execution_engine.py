from typing import Any

class ExecutionEngine:
    def __init__(self) -> None:
        pass

    def calculate_execution_zones(self, close_price: float, atr: float, volatility_mult: float = 1.0) -> dict[str, Any]:
        """
        Calculate volatility-adjusted execution thresholds:
        - ATR-based Stop Loss: close - 1.5 * ATR * volatility_mult
        - Trailing SL: close - 2.0 * ATR * volatility_mult
        - Target 1 (Partial exit 50%): close + 1.5 * ATR * volatility_mult
        - Target 2 (Final exit 50%): close + 3.0 * ATR * volatility_mult
        """
        # Default ATR estimate if zero
        atr = atr if atr > 0 else (close_price * 0.015)
        
        sl = round(close_price - (1.5 * atr * volatility_mult), 2)
        trailing_sl = round(close_price - (2.0 * atr * volatility_mult), 2)
        target1 = round(close_price + (1.5 * atr * volatility_mult), 2)
        target2 = round(close_price + (3.0 * atr * volatility_mult), 2)
        
        return {
            "entry": round(close_price, 2),
            "sl": sl,
            "trailing_sl": trailing_sl,
            "target1": target1,
            "target2": target2,
            "risk_reward": round((target1 - close_price) / (close_price - sl), 2) if (close_price - sl) > 0 else 2.0
        }

    def evaluate_entry(
        self,
        close_price: float,
        prev_close: float,
        ema_9: float,
        prev_ema_9: float,
        volume: int,
        avg_volume: int,
        atr: float,
        vwap: float | None = None,
    ) -> dict[str, Any]:
        """
        Evaluates long entry conditions based on 15m candle data with ATR targets.
        """
        entry_confirmed = False
        reasons = []

        if close_price > ema_9 and prev_close <= prev_ema_9:
            entry_confirmed = True
            reasons.append("15m close above 9 EMA")

            if volume > avg_volume:
                reasons.append("Volume confirmation (above avg)")
            if vwap and close_price > vwap:
                reasons.append("VWAP confirmation (price > VWAP)")

        zones = self.calculate_execution_zones(close_price, atr)
        
        return {
            "entry_confirmed": entry_confirmed,
            "reasons": reasons,
            "execution_zones": zones
        }

    def evaluate_exit(
        self,
        close_prices: list[float],
        ema_9_values: list[float],
        current_price: float,
        avg_price: float,  # Average entry price
        atr: float,
        vwap: float | None = None,
        highest_since_entry: float = 0.0
    ) -> dict[str, Any]:
        """
        Evaluates long exit conditions including Trailing SL and Partial target exits.
        """
        if len(close_prices) < 2 or len(ema_9_values) < 2:
            return {"exit_signal": False, "severity": "none", "reason": "Insufficient candles"}

        c0, c1 = close_prices[-1], close_prices[-2]
        e0, e1 = ema_9_values[-1], ema_9_values[-2]

        # 1. Volatility target & Stop Loss check
        zones = self.calculate_execution_zones(avg_price, atr)
        
        # Trailing SL check: trailing SL locks in gains
        trailing_sl_threshold = highest_since_entry - (1.5 * atr) if highest_since_entry > avg_price else zones["sl"]
        if current_price <= trailing_sl_threshold:
            return {"exit_signal": True, "severity": "hard", "reason": "Trailing Stop Loss breached"}

        # Partial Target checks
        if current_price >= zones["target2"]:
            return {"exit_signal": True, "severity": "hard", "reason": "Final target achieved"}
        elif current_price >= zones["target1"]:
            return {"exit_signal": True, "severity": "partial", "reason": "Target 1 achieved (Exit 50%)"}

        # 2. EMA close checks
        soft_exit = c0 < e0
        hard_exit = (c0 < e0) and (c1 < e1)
        
        if hard_exit and vwap and c0 < vwap:
            return {"exit_signal": True, "severity": "hard", "reason": "2 consecutive 15m closes below EMA + VWAP breach"}
        if hard_exit:
            return {"exit_signal": True, "severity": "hard", "reason": "2 consecutive 15m closes below EMA"}
        if soft_exit:
            return {"exit_signal": True, "severity": "soft", "reason": "15m close below 9 EMA"}
            
        return {"exit_signal": False, "severity": "none", "reason": "Trend is holding"}

# Global Instance
execution_engine = ExecutionEngine()
