from typing import Any


class FibonacciEngine:
    def __init__(self):
        self.retracements = [0.236, 0.382, 0.500, 0.618, 0.786]
        self.extensions = [1.272, 1.618, 2.618]

    def compute_levels(self, swing_high: float, swing_low: float, trend: str = "UP") -> dict[str, Any]:
        """
        Computes Fibonacci retracement and extension levels based on swing points.
        Trend 'UP': Pullbacks act as support, extensions act as upper targets.
        Trend 'DOWN': Pullbacks act as resistance, extensions act as lower targets.
        """
        diff = swing_high - swing_low
        if diff <= 0:
            return {}

        results = {}
        
        if trend == "UP":
            # Retracements from Swing High downwards
            for r in self.retracements:
                key = f"fib_{str(r).split('.')[1].ljust(3, '0')}"
                if r == 0.500:
                    key = "fib_50"
                results[key] = round(swing_high - (diff * r), 2)
            
            # Extensions above Swing High
            for e in self.extensions:
                key = f"ext_{str(e).replace('.', '')}"
                results[key] = round(swing_high + (diff * (e - 1.0)), 2)
                
        elif trend == "DOWN":
            # Retracements from Swing Low upwards
            for r in self.retracements:
                key = f"fib_{str(r).split('.')[1].ljust(3, '0')}"
                if r == 0.500:
                    key = "fib_50"
                results[key] = round(swing_low + (diff * r), 2)
                
            # Extensions below Swing Low
            for e in self.extensions:
                key = f"ext_{str(e).replace('.', '')}"
                results[key] = round(swing_low - (diff * (e - 1.0)), 2)

        return results

    def find_confluence(self, current_price: float, levels: dict[str, float], threshold_pct: float = 0.5) -> list[str]:
        """
        Checks if current_price is near any of the Fibonacci levels (confluence zones).
        """
        confluences = []
        for name, price in levels.items():
            dist = abs((current_price - price) / price) * 100
            if dist <= threshold_pct:
                confluences.append(f"Near {name} ({price})")
        return confluences
