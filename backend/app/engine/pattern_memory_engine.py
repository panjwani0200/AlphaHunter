import numpy as np
from typing import Any
from app.domain.contracts import MarketCandle

class PatternMemoryEngine:
    def __init__(self, window_size: int = 20) -> None:
        self.window_size = window_size

    def _extract_features(self, candles: list[MarketCandle], start_idx: int) -> np.ndarray:
        """
        Extract normalized features for a window of size window_size starting at start_idx.
        Features per candle:
        1. Price change relative to window start close.
        2. Volume relative to rolling volume (estimated by window average).
        3. RSI estimate (relative close within high/low range of window).
        4. ATR estimate (high-low spread normalized by close).
        """
        window = candles[start_idx : start_idx + self.window_size]
        base_close = window[0].close if window[0].close else 1.0
        
        features = []
        for c in window:
            # 1. Price relative to base close
            p_rel = (c.close - base_close) / base_close if base_close else 0.0
            
            # 2. Spread/Volatility estimate
            hl_spread = (c.high - c.low) / c.close if c.close else 0.0
            
            # 3. Volume ratio (relative to window average)
            avg_vol = sum(w.volume for w in window) / len(window)
            vol_ratio = c.volume / avg_vol if avg_vol > 0 else 1.0
            
            features.extend([p_rel, hl_spread, vol_ratio])
            
        return np.array(features, dtype=float)

    def find_similar_setups(self, candles: list[MarketCandle], similarity_threshold: float = 0.85) -> dict[str, Any]:
        """
        Compares the current window (latest window_size candles) against all historical windows.
        Calculates similarity scores and tracks subsequent 1, 3, 5, and 10 day returns.
        """
        n_candles = len(candles)
        if n_candles < self.window_size + 10:
            return {
                "matches_found": 0,
                "win_rate": 0.0,
                "avg_return_3d": 0.0,
                "avg_return_5d": 0.0,
                "max_drawdown": 0.0
            }

        # Current state is the last window_size candles
        current_idx = n_candles - self.window_size
        current_vector = self._extract_features(candles, current_idx)
        current_norm = np.linalg.norm(current_vector)

        matches = []
        # Slide historical window up to current_idx - 10 (to allow 10-day lookahead)
        for i in range(0, current_idx - 10):
            hist_vector = self._extract_features(candles, i)
            hist_norm = np.linalg.norm(hist_vector)
            
            if current_norm > 0 and hist_norm > 0:
                similarity = np.dot(current_vector, hist_vector) / (current_norm * hist_norm)
            else:
                similarity = 0.0

            if similarity >= similarity_threshold:
                # Setup trigger candle at index i + window_size - 1
                trigger_price = candles[i + self.window_size - 1].close
                
                # Check forward performance
                ret_3d = ((candles[i + self.window_size + 2].close - trigger_price) / trigger_price) * 100
                ret_5d = ((candles[i + self.window_size + 4].close - trigger_price) / trigger_price) * 100
                ret_10d = ((candles[i + self.window_size + 9].close - trigger_price) / trigger_price) * 100
                
                # Calculate max drawdown in the next 10 days
                forward_period = candles[i + self.window_size : i + self.window_size + 10]
                lows = [c.low for c in forward_period]
                max_dd = ((min(lows) - trigger_price) / trigger_price) * 100 if lows else 0.0

                matches.append({
                    "ret_3d": ret_3d,
                    "ret_5d": ret_5d,
                    "ret_10d": ret_10d,
                    "max_dd": max_dd,
                    "success": ret_5d > 0.0
                })

        if not matches:
            return {
                "matches_found": 0,
                "win_rate": 0.5,
                "avg_return_3d": 0.0,
                "avg_return_5d": 0.0,
                "max_drawdown": 0.0
            }

        n_matches = len(matches)
        win_rate = sum(1 for m in matches if m["success"]) / n_matches
        avg_3d = sum(m["ret_3d"] for m in matches) / n_matches
        avg_5d = sum(m["ret_5d"] for m in matches) / n_matches
        avg_dd = sum(m["max_dd"] for m in matches) / n_matches

        return {
            "matches_found": n_matches,
            "win_rate": round(win_rate, 2),
            "avg_return_3d": round(avg_3d, 2),
            "avg_return_5d": round(avg_5d, 2),
            "max_drawdown": round(avg_dd, 2)
        }
