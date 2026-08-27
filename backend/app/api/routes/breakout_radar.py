from fastapi import APIRouter
from app.domain.contracts import BreakoutRadarCandidate
from app.engine.breakout_radar import breakout_radar_engine
from app.services.trading_service import trading_service

router = APIRouter(prefix="/breakout-radar")

@router.get("/latest", response_model=list[BreakoutRadarCandidate])
async def latest_breakout_radar():
    snapshots = await trading_service.get_snapshots()
    candidates = await breakout_radar_engine.scan_market(snapshots)
    return candidates

@router.post("/test-telegram")
async def test_telegram_breakout():
    from app.domain.contracts import AlertMessage, AlertType
    from app.alerts.telegram import TelegramNotifier
    from datetime import datetime, timezone
    
    msg = (
        f"🚨 <b>BREAKOUT ALERT</b> 🚨\n\n"
        f"<b>Symbol:</b> RELIANCE\n"
        f"<b>Price:</b> ₹2950.0\n"
        f"<b>Month High:</b> ₹2945.0\n"
        f"<b>Month Low:</b> ₹2750.0\n"
        f"<b>Score:</b> 85%\n"
        f"<b>Entry:</b> 2955\n"
        f"<b>Stoploss:</b> ₹2920\n"
        f"<b>Targets:</b> ₹3000, ₹3050\n\n"
        f"<i>AI detected strong volume buildup and momentum breakout above key resistance.</i>"
    )
    alert = AlertMessage(
        alert_type=AlertType.BREAKOUT,
        symbol="RELIANCE",
        title="Breakout Alert", 
        message=msg,
        triggered_at=datetime.now(timezone.utc)
    )
    notifier = TelegramNotifier()
    success = notifier.send(alert)
    return {"success": success, "message": "Test breakout alert sent to Telegram"}
