import asyncio
import json
import urllib.request
from app.alerts.telegram import TelegramNotifier
from app.domain.contracts import AlertMessage, AlertType, AlertAction
from datetime import datetime, timezone

def send_table():
    req = urllib.request.urlopen('http://127.0.0.1:8000/api/breakout-radar/latest')
    candidates = json.loads(req.read().decode('utf-8'))
    
    filtered = [
        c for c in candidates
        if c['status'] in ("Confirmed Breakout", "Near Breakout")
        or (c['confidence_score'] <= 20)
    ]
    
    if filtered:
        msg = "📊 <b>CURRENT BREAKOUT RADAR</b>\n\n<pre>"
        msg += f"{'SYMBOL':<10}|{'PRICE':<7}|{'STATUS':<6}|{'SCR'}\n"
        msg += "-" * 31 + "\n"
        for c in filtered:
            sym = c['symbol'][:10]
            price = str(round(c['last_price'], 1))
            
            # Shorten status for mobile
            stat_val = c['status']
            if stat_val == "Confirmed Breakout": stat = "BrkOut"
            elif stat_val == "Near Breakout": stat = "Near"
            elif c['confidence_score'] <= 20: stat = "Bear"
            else: stat = stat_val[:6]
            
            score = f"{c['confidence_score']}%"
            msg += f"{sym:<10}|{price:<7}|{stat:<6}|{score:>3}\n"
            
            h = round(c['prev_month_high'], 1)
            l = round(c['prev_month_low'], 1)
            msg += f" ↳ H:{h} L:{l}\n"
            
        msg += "</pre>"
            
        notifier = TelegramNotifier()
        alert = AlertMessage(
            alert_type=AlertType.BREAKOUT,
            symbol="RADAR",
            title="Breakout Radar Table",
            message=msg,
            action=AlertAction.WATCH,
            triggered_at=datetime.now(timezone.utc)
        )
        notifier.send(alert)
        print("Sent!")
    else:
        print("No candidates matched the filter.")

if __name__ == "__main__":
    send_table()
