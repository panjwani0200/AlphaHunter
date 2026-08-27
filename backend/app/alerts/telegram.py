from __future__ import annotations

import httpx

from app.core.config import settings
from app.domain.contracts import AlertAction, AlertMessage, AlertType


def _score_bar(score: float, length: int = 10) -> str:
    filled = round((score / 100.0) * length)
    return "▓" * filled + "░" * (length - filled)


def _format_scanner_alert(alert: AlertMessage) -> str:
    payload = alert.payload or {}
    if not payload and alert.message:
        return alert.message
    score = alert.score or 0.0
    symbol = alert.symbol or payload.get("symbol", "?")
    signal = str(payload.get("signal_type", "")).replace("_", " ").upper()
    evidence = payload.get("evidence", {})

    price = evidence.get("last_price")
    rsi = evidence.get("rsi_14")
    oi_interp = str(evidence.get("oi_interpretation") or "").replace("_", " ")
    reasons = payload.get("reasons", [])[:3]
    conflicts = payload.get("conflicts", [])[:2]

    bar = _score_bar(score)
    reason_lines = "\n".join(f"  • {r}" for r in reasons) if reasons else "  • No specific reasons noted"
    conflict_lines = (
        "\n".join(f"  ⚠️ {c}" for c in conflicts) if conflicts else ""
    )

    lines = [
        f"🎯 <b>{symbol}</b> — {signal}",
        f"Score: <code>{bar} {score:.0f}/100</code>",
    ]
    if price:
        lines.append(f"Price: ₹{price:,.2f}")
    if rsi:
        lines.append(f"RSI-14: {rsi:.1f}")
    if oi_interp:
        lines.append(f"OI: {oi_interp}")
    lines.append("\n<b>Evidence:</b>")
    lines.append(reason_lines)
    if conflict_lines:
        lines.append("\n<b>Risks:</b>")
        lines.append(conflict_lines)
    return "\n".join(lines)


def _format_portfolio_summary(alert: AlertMessage) -> str:
    return f"📊 <b>{alert.title}</b>\n\n{alert.message}"


def _format_daily_report(alert: AlertMessage) -> str:
    return f"📈 <b>{alert.title}</b>\n\n{alert.message}"


def _format_reversal_alert(alert: AlertMessage) -> str:
    action_emoji = {
        AlertAction.HOLD: "✅",
        AlertAction.WATCH: "⚠️",
        AlertAction.REDUCE: "🟠",
        AlertAction.EXIT: "🔴",
    }.get(alert.action, "•")
    return (
        f"{action_emoji} <b>{alert.symbol or ''} — {alert.action.value.upper()}</b>\n\n"
        f"{alert.message}"
    )


def _build_message_text(alert: AlertMessage) -> str:
    if alert.symbol == "CONSOLIDATED":
        return alert.message
        
    if alert.alert_type in {AlertType.BREAKOUT, AlertType.SWING_ENTRY, AlertType.LONG_BUILDUP, AlertType.SHORT_BUILDUP}:
        return _format_scanner_alert(alert)
    if alert.alert_type == AlertType.PORTFOLIO_SUMMARY:
        return _format_portfolio_summary(alert)
    if alert.alert_type == AlertType.DAILY_REPORT:
        return _format_daily_report(alert)
    if alert.alert_type == AlertType.REVERSAL:
        return _format_reversal_alert(alert)
    # Default
    return f"<b>{alert.title}</b>\n\n{alert.message}"


class TelegramNotifier:
    def __init__(self) -> None:
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send(self, alert: AlertMessage) -> bool:
        if not self.enabled:
            return False
            
        from datetime import datetime, timezone, timedelta
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        
        # 1. Block Weekends (5 = Saturday, 6 = Sunday)
        if now.weekday() >= 5:
            return False
            
        # 2. Block outside 09:15 AM to 03:30 PM (IST)
        current_time_minutes = now.hour * 60 + now.minute
        if current_time_minutes < (9 * 60 + 15) or current_time_minutes > (15 * 60 + 30):
            return False
            
        text = _build_message_text(alert)
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            response = httpx.post(
                url,
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"},
                timeout=15,
            )
            response.raise_for_status()
        except Exception:
            return False
        return True
