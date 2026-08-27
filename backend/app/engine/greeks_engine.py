import math
from app.domain.contracts import OptionGreeks, PremiumBehavior

# Basic Black-Scholes approximations
def calculate_greeks(
    spot: float,
    strike: float,
    time_to_expiry_days: float,
    volatility: float,
    risk_free_rate: float = 0.07,
    option_type: str = "CE"
) -> OptionGreeks:
    t = max(time_to_expiry_days / 365.0, 0.0001)
    v = max(volatility, 0.0001)
    
    d1 = (math.log(spot / strike) + (risk_free_rate + (v ** 2) / 2) * t) / (v * math.sqrt(t))
    d2 = d1 - v * math.sqrt(t)
    
    # Cumulative normal distribution approx
    def norm_cdf(x: float) -> float:
        return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0
    
    # PDF approx
    def norm_pdf(x: float) -> float:
        return math.exp(-0.5 * x ** 2) / math.sqrt(2 * math.pi)

    if option_type == "CE":
        delta = norm_cdf(d1)
    else:
        delta = norm_cdf(d1) - 1.0

    gamma = norm_pdf(d1) / (spot * v * math.sqrt(t))
    vega = spot * norm_pdf(d1) * math.sqrt(t) / 100.0  # per 1% change in vol
    
    if option_type == "CE":
        theta = (- (spot * v * norm_pdf(d1)) / (2 * math.sqrt(t)) 
                 - risk_free_rate * strike * math.exp(-risk_free_rate * t) * norm_cdf(d2)) / 365.0
        rho = strike * t * math.exp(-risk_free_rate * t) * norm_cdf(d2) / 100.0
    else:
        theta = (- (spot * v * norm_pdf(d1)) / (2 * math.sqrt(t)) 
                 + risk_free_rate * strike * math.exp(-risk_free_rate * t) * norm_cdf(-d2)) / 365.0
        rho = -strike * t * math.exp(-risk_free_rate * t) * norm_cdf(-d2) / 100.0

    # Mock IV Rank and Percentile for now
    iv_percentile = 55.0
    iv_rank = 50.0

    return OptionGreeks(
        delta=round(delta, 4),
        gamma=round(gamma, 4),
        theta=round(theta, 4),
        vega=round(vega, 4),
        rho=round(rho, 4),
        iv_percentile=iv_percentile,
        iv_rank=iv_rank
    )

def analyze_premium_behavior(
    spot_change: float,
    premium_change: float,
    greeks: OptionGreeks,
    iv_change: float
) -> PremiumBehavior:
    reasons = []
    behavior = "NORMAL"

    if spot_change > 0.5 and premium_change < 0.1:
        behavior = "STAGNANT"
        if iv_change < 0:
            reasons.append("IV contraction")
        if greeks.theta < -10:
            reasons.append("High Theta decay")
        if greeks.gamma < 0.05:
            reasons.append("Low Gamma")
    elif spot_change < -0.5 and premium_change > -0.1:
        behavior = "RESILIENT"
        if iv_change > 0:
            reasons.append("IV expansion shielding decay")
    else:
        behavior = "EXPECTED"
        reasons.append("Premium tracking delta")

    if not reasons:
        reasons.append("Unknown structural drag")

    return PremiumBehavior(
        premium_behavior=behavior,
        reason=reasons
    )
