from typing import Any

class OrderFlowEngine:
    def __init__(self) -> None:
        pass

    def evaluate_order_flow(self, last_price: float, high: float, low: float, volume: int, avg_volume_20d: float) -> dict[str, Any]:
        """
        Evaluate order flow buying/selling pressure based on transaction footprint:
        - Bid-ask imbalance ratio (calculated from close price relative to daily low/high)
        - Absorption level (volume compared to 20-day average)
        - Aggressive buyer vs seller pressure
        """
        price_range = high - low
        if price_range <= 0:
            return {
                "buy_pressure": 0.5,
                "sell_pressure": 0.5,
                "imbalance_ratio": 1.0,
                "absorption_state": "NEUTRAL",
                "order_book_pressure": 0.5
            }

        # Imbalance ratio: closer to high means aggressive buying (bids winning)
        raw_imbalance = (last_price - low) / price_range
        # Smooth and bound to 0.05 to 0.95
        buy_pressure = round(0.05 + 0.90 * raw_imbalance, 2)
        sell_pressure = round(1.0 - buy_pressure, 2)

        # Absorption: high volume near range extremes means institutional absorption
        volume_mult = volume / avg_volume_20d if avg_volume_20d > 0 else 1.0
        
        if volume_mult > 1.8:
            if buy_pressure > 0.7:
                absorption_state = "BULLISH_ABSORPTION"  # Selling pressure absorbed by strong buyers
            elif sell_pressure > 0.7:
                absorption_state = "BEARISH_ABSORPTION"  # Buying pressure absorbed by strong sellers
            else:
                absorption_state = "HIGH_VOLUME_CHURN"
        else:
            absorption_state = "NORMAL_LIQUIDITY"

        # Order book pressure: weighted average of buy pressure and volume multiplier
        order_book_pressure = round((buy_pressure * 0.7) + (min(2.0, volume_mult) / 2.0 * 0.3), 2)

        return {
            "buy_pressure": buy_pressure,
            "sell_pressure": sell_pressure,
            "imbalance_ratio": round(buy_pressure / (sell_pressure or 0.01), 2),
            "absorption_state": absorption_state,
            "order_book_pressure": order_book_pressure
        }

# Global Instance
order_flow_engine = OrderFlowEngine()
