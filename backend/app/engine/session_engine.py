from datetime import datetime
from app.domain.contracts import SessionResult

def evaluate_session(observed_at: datetime) -> SessionResult:
    # observed_at is typically UTC, but we want Indian Standard Time (IST)
    # UTC to IST is +5:30. Let's just do a naive hours calculation assuming we convert it or it's provided correctly.
    # For simplicity, assuming observed_at has timezone info or is already localized appropriately by the system.
    # In this mock system, we'll convert strictly by hours and minutes in IST.
    
    # We will assume observed_at is UTC and add 5.5 hours to get IST.
    ist_time = observed_at.timestamp() + (5.5 * 3600)
    ist_dt = datetime.fromtimestamp(ist_time)
    
    hour = ist_dt.hour
    minute = ist_dt.minute
    time_val = hour + minute / 60.0
    
    # 9:15 = 9.25, 9:45 = 9.75, 11:30 = 11.5, 13:30 = 13.5, 15:30 = 15.5
    
    if 9.25 <= time_val < 9.75:
        return SessionResult(session_quality="HIGH", score=90)  # Opening volatility
    elif 9.75 <= time_val < 11.5:
        return SessionResult(session_quality="HIGH", score=95)  # Trend expansion
    elif 11.5 <= time_val < 13.5:
        return SessionResult(session_quality="LOW", score=50)   # Low probability zone
    elif 13.5 <= time_val <= 15.5:
        return SessionResult(session_quality="HIGH", score=90)  # Closing momentum
        
    return SessionResult(session_quality="LOW", score=40) # Outside hours
