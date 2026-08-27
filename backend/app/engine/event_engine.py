from app.domain.contracts import EventRisk

# Mock static calendar for demonstration of Event Engine
# In production, this would query a corporate actions DB
UPCOMING_EVENTS = {
    "BEL": {"event": "Quarterly Results in 2 days", "risk": "HIGH"},
    "CDSL": {"event": "Board meeting for bonus issue tomorrow", "risk": "CRITICAL"},
    "ADANIPOWER": {"event": "AGM next week", "risk": "MODERATE"},
    "NIFTY": {"event": "RBI Policy announcement at 10 AM", "risk": "CRITICAL"},
    "BANKNIFTY": {"event": "RBI Policy announcement at 10 AM", "risk": "CRITICAL"}
}

def evaluate_event_risk(symbol: str) -> EventRisk:
    """
    Check if there are any upcoming events for the symbol that pose a risk.
    """
    sym_upper = symbol.upper()
    if sym_upper in UPCOMING_EVENTS:
        info = UPCOMING_EVENTS[sym_upper]
        return EventRisk(
            symbol=sym_upper,
            event_risk=info["risk"],
            event=info["event"]
        )
        
    return EventRisk(
        symbol=sym_upper,
        event_risk="LOW",
        event="No major upcoming events in next 7 days"
    )
