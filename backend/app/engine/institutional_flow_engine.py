from typing import Any

class InstitutionalFlowEngine:
    def __init__(self) -> None:
        pass

    def evaluate_flows(self, symbol: str) -> dict[str, Any]:
        """
        Track daily FII (Foreign Institutional) and DII (Domestic Institutional) cash flows
        and derivatives position long/short ratios to output a unified sentiment score.
        """
        # In a real environment this queries a database populated by daily EOD reports.
        # We scaffold the data structures and populate with typical current values for NSE FNO stocks.
        
        # Static representative data for NSE large caps
        net_flows = {
            "RELIANCE": {"fii_net_cr": 120.5, "dii_net_cr": 85.2, "derivatives_long_ratio": 0.62},
            "HDFCBANK": {"fii_net_cr": -350.2, "dii_net_cr": 410.5, "derivatives_long_ratio": 0.48},
            "INFY": {"fii_net_cr": 45.1, "dii_net_cr": -12.3, "derivatives_long_ratio": 0.55},
            "TATAMOTORS": {"fii_net_cr": 95.8, "dii_net_cr": 15.6, "derivatives_long_ratio": 0.70},
            "BEL": {"fii_net_cr": 15.2, "dii_net_cr": 32.4, "derivatives_long_ratio": 0.65},
            "NIFTY": {"fii_net_cr": -210.0, "dii_net_cr": 540.0, "derivatives_long_ratio": 0.54},
            "BANKNIFTY": {"fii_net_cr": -480.0, "dii_net_cr": 690.0, "derivatives_long_ratio": 0.51}
        }
        
        data = net_flows.get(symbol.upper(), {"fii_net_cr": 10.0, "dii_net_cr": 15.0, "derivatives_long_ratio": 0.50})
        
        # Calculate institutional sentiment score (0 to 100)
        # 50 is neutral. Positive flows and high long ratio raise the score.
        score = 50.0
        
        # Add weights for cash flows
        fii_contrib = max(-25.0, min(25.0, data["fii_net_cr"] / 10.0))
        dii_contrib = max(-15.0, min(15.0, data["dii_net_cr"] / 15.0))
        
        # Add weights for derivatives positioning (0.5 is neutral)
        deriv_contrib = (data["derivatives_long_ratio"] - 0.5) * 100.0  # max +/- 50
        
        score += fii_contrib + dii_contrib + deriv_contrib
        score = max(5.0, min(98.0, round(score, 2)))
        
        # Labeling sentiment
        if score > 75:
            sentiment = "VERY_BULLISH"
        elif score > 60:
            sentiment = "BULLISH"
        elif score > 40:
            sentiment = "NEUTRAL"
        elif score > 25:
            sentiment = "BEARISH"
        else:
            sentiment = "VERY_BEARISH"
            
        return {
            "fii_net_cr": data["fii_net_cr"],
            "dii_net_cr": data["dii_net_cr"],
            "derivatives_long_ratio": data["derivatives_long_ratio"],
            "sentiment_score": score,
            "sentiment": sentiment
        }

# Global Instance
institutional_flow_engine = InstitutionalFlowEngine()
