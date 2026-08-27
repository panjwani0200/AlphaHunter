from typing import Any

from app.domain.contracts import OptionChainAnalysis


class OptionsPredictionEngine:
    def __init__(self):
        pass

    def predict(
        self,
        current_price: float,
        chain: OptionChainAnalysis,
        iv: float | None = None,
    ) -> dict[str, Any]:
        """
        Takes an OptionChainAnalysis and generates a predictive summary.
        """
        support = chain.max_put_oi_strike
        resistance = chain.max_call_oi_strike
        
        bullish_prob = 50
        
        # Adjust probability based on PCR
        if chain.pcr:
            if chain.pcr > 1.2:
                bullish_prob += 15
            elif chain.pcr < 0.7:
                bullish_prob -= 15
                
        # Max pain bias
        if chain.max_pain:
            dist = (current_price - chain.max_pain) / chain.max_pain
            if dist < -0.01:
                # Price is below max pain -> pull upwards towards max pain
                bullish_prob += 10
            elif dist > 0.01:
                # Price is above max pain -> pull downwards
                bullish_prob -= 10
                
        # Price vs Walls
        if support and current_price < support:
            # Breakdown of support
            bullish_prob -= 15
        if resistance and current_price > resistance:
            # Breakout of resistance
            bullish_prob += 15
            
        bullish_prob = max(0, min(100, bullish_prob))
        
        expiry_range = f"{support or 'N/A'} - {resistance or 'N/A'}"
        
        target_if_breakout = None
        if resistance and support:
            width = resistance - support
            if current_price >= resistance:
                target_if_breakout = resistance + width
                
        return {
            "support": support,
            "resistance": resistance,
            "expiry_range": expiry_range,
            "bullish_probability": bullish_prob,
            "target_if_breakout": target_if_breakout,
            "max_pain": chain.max_pain,
        }
