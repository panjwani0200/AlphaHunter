from app.domain.contracts import TradeCard, ExitSignal
import logging

logger = logging.getLogger("uvicorn")

class NotificationEnginePro:
    
    @staticmethod
    def format_trade_alert(card: TradeCard) -> str:
        targets_str = " / ".join(str(t) for t in card.targets)
        return (
            f"ALPHAHUNTER SIGNAL\n\n"
            f"{card.signal} {card.symbol}\n"
            f"Entry: {card.entry}\n"
            f"SL: {card.stop_loss}\n"
            f"Target: {targets_str}\n"
            f"Confidence: {card.confidence}%\n"
            f"Option: {card.options_recommendation}"
        )
        
    @staticmethod
    def format_exit_alert(exit_signal: ExitSignal) -> str:
        return (
            f"ALPHAHUNTER EXIT ALERT\n\n"
            f"Action: {exit_signal.action} {exit_signal.symbol}\n"
            f"Reason: {exit_signal.reason}"
        )
        
    @staticmethod
    def format_cycle_alert(symbol: str, phase: str, confidence: float, recommended_action: str) -> str:
        return (
            f"ALPHAHUNTER CYCLE ALERT\n\n"
            f"{symbol} entering {phase}\n"
            f"Probability: {confidence}%\n"
            f"{recommended_action}"
        )
        
    @staticmethod
    def send_telegram_alert(message: str) -> None:
        from zoneinfo import ZoneInfo
        from datetime import time, datetime
        
        # Enforce strict market hour timings for Telegram
        now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
        if now_ist.weekday() >= 5: # Saturday or Sunday
            return
        if not (time(9, 15) <= now_ist.time() <= time(15, 30)):
            return
            
        # Placeholder for actual telegram integration
        logger.info(f"[TELEGRAM] {message.replace(chr(10), ' | ')}")
        
    @staticmethod
    def send_web_push(message: str) -> None:
        # Placeholder for web push 
        logger.info(f"[WEB PUSH] {message.replace(chr(10), ' | ')}")
        
    @staticmethod
    def send_sound_alert() -> None:
        # Triggers a websocket event to play sound on frontend
        logger.info("[SOUND ALERT] Beep beep")
        
    @classmethod
    def dispatch_trade_card(cls, card: TradeCard) -> None:
        msg = cls.format_trade_alert(card)
        cls.send_telegram_alert(msg)
        cls.send_web_push(msg)
        cls.send_sound_alert()

    @classmethod
    def dispatch_exit_signal(cls, exit_signal: ExitSignal) -> None:
        msg = cls.format_exit_alert(exit_signal)
        cls.send_telegram_alert(msg)
        cls.send_web_push(msg)
        cls.send_sound_alert()

    @classmethod
    def dispatch_cycle_alert(cls, symbol: str, phase: str, confidence: float, recommended_action: str) -> None:
        from zoneinfo import ZoneInfo
        from datetime import time, datetime
        
        # Only send notifications during market hours (9:15 - 15:30 IST, Mon-Fri)
        now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
        if now_ist.weekday() >= 5: # Saturday or Sunday
            return
        if not (time(9, 15) <= now_ist.time() <= time(15, 30)):
            return

        msg = cls.format_cycle_alert(symbol, phase, confidence, recommended_action)
        cls.send_telegram_alert(msg)
        cls.send_web_push(msg)
        cls.send_sound_alert()
