import asyncio
import logging
import httpx
from app.core.config import settings
from app.services.trading_service import trading_service
from app.domain.contracts import PositionInput, InstrumentType

logger = logging.getLogger("uvicorn")

class TelegramBotListener:
    def __init__(self) -> None:
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.running = False
        self._task: asyncio.Task | None = None
        self._offset = 0

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token)

    def start(self) -> None:
        if not self.enabled:
            logger.warning("Telegram bot token not configured. Bot listener not started.")
            return
        self.running = True
        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._poll_loop())
        logger.info("Telegram Bot Listener started.")

    def stop(self) -> None:
        self.running = False
        if self._task:
            self._task.cancel()
        logger.info("Telegram Bot Listener stopped.")

    async def _poll_loop(self) -> None:
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        async with httpx.AsyncClient(timeout=15) as client:
            while self.running:
                try:
                    params = {"offset": self._offset, "timeout": 10}
                    response = await client.get(url, params=params)
                    if response.status_code != 200:
                        await asyncio.sleep(5)
                        continue
                    
                    data = response.json()
                    if not data.get("ok"):
                        await asyncio.sleep(5)
                        continue
                    
                    updates = data.get("result", [])
                    for update in updates:
                        self._offset = update["update_id"] + 1
                        message = update.get("message")
                        if message:
                            await self._handle_message(message, client)
                            
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in Telegram Bot poll loop: {e}")
                    await asyncio.sleep(5)

    async def _handle_message(self, message: dict, client: httpx.AsyncClient) -> None:
        chat_id = message["chat"]["id"]
        # If settings.telegram_chat_id is specified, we should only listen to that user/group
        if self.chat_id and str(chat_id) != str(self.chat_id):
            return
            
        text = message.get("text", "").strip()
        if not text:
            return

        reply = ""
        cmd = text.split()[0].lower() if text else ""

        if cmd == "/start":
            reply = (
                "👋 <b>Welcome to AlphaHunter AI Trading Copilot</b>\n\n"
                "I am your quant bot powered by rules + AI models.\n\n"
                "<b>Commands:</b>\n"
                "• /overview — Market Nifty trend & sectors\n"
                "• /scan — Top momentum/breakout/reversal symbols\n"
                "• /positions — Status of current open positions\n"
                "• /daily — Generate daily market intelligence report\n"
                "• /execute <code>[SYMBOL] [ENTRY] [QTY]</code> — Place manual position call\n"
            )
        elif cmd == "/overview":
            try:
                overview = await trading_service.market_overview()
                reply = (
                    f"📊 <b>NIFTY 50:</b> {overview.nifty_trend.upper()}\n\n"
                    f"🟢 <b>Strong Sectors:</b> {', '.join(overview.strongest_sectors)}\n"
                    f"🔴 <b>Weak Sectors:</b> {', '.join(overview.weakest_sectors)}\n"
                    f"🔥 <b>Hot Symbols:</b> {', '.join(overview.hot_symbols)}\n\n"
                    f"⚠️ <b>Risk Notes:</b>\n" + "\n".join(f"• {n}" for n in overview.risk_notes)
                )
            except Exception as e:
                reply = f"Error fetching overview: {e}"
        elif cmd == "/scan":
            try:
                candidates = await trading_service.run_scan(limit=3)
                if not candidates:
                    reply = "📡 No scanning candidates found above threshold."
                else:
                    lines = ["📡 <b>Top Scanner Opportunities:</b>\n"]
                    for c in candidates:
                        lines.append(
                            f"• <b>{c.symbol}</b> ({c.signal_type.value.replace('_', ' ').upper()})\n"
                            f"  Score: <code>{c.score:.0f}/100</code> | Entry Zone suggestion in dashboard"
                        )
                    reply = "\n".join(lines)
            except Exception as e:
                reply = f"Error running scan: {e}"
        elif cmd == "/positions":
            try:
                positions = await trading_service.list_positions()
                if not positions:
                    reply = "📂 No active open positions."
                else:
                    lines = ["📂 <b>Current Positions:</b>\n"]
                    for p in positions:
                        pnl_sign = "+" if p.pnl_percent > 0 else ""
                        lines.append(
                            f"• <b>{p.symbol}</b> (Long)\n"
                            f"  Entry: ₹{p.entry_price:.2f} | LTP: ₹{p.latest_price:.2f}\n"
                            f"  PnL: <b>{pnl_sign}{p.pnl_percent}%</b> | Health: {p.health_score or 0:.0f}/100"
                        )
                    reply = "\n".join(lines)
            except Exception as e:
                reply = f"Error listing positions: {e}"
        elif cmd == "/daily":
            try:
                report = await trading_service.daily_report()
                reply = f"📈 <b>{report.title}</b>\n\n{report.message}"
            except Exception as e:
                reply = f"Error generating report: {e}"
        elif cmd == "/execute":
            parts = text.split()
            if len(parts) < 4:
                reply = "⚠️ Usage: /execute <code>[SYMBOL] [ENTRY] [QTY]</code>\nExample: /execute RELIANCE 1313.4 10"
            else:
                try:
                    symbol = parts[1].upper()
                    entry_price = float(parts[2])
                    qty = int(parts[3])
                    pos = await trading_service.add_position(PositionInput(
                        symbol=symbol,
                        entry_price=entry_price,
                        quantity=qty,
                        instrument_type=InstrumentType.EQUITY
                    ))
                    reply = (
                        f"✅ <b>Position Added Successfully</b>\n\n"
                        f"• Symbol: {pos.symbol}\n"
                        f"• Entry Price: ₹{pos.entry_price:.2f}\n"
                        f"• Qty: {pos.quantity}\n"
                        f"• Health: {pos.health_score or 0:.0f}/100"
                    )
                except Exception as e:
                    reply = f"⚠️ Failed to add position: {e}"
        else:
            reply = "❓ Unknown command. Type /start for list of commands."

        if reply:
            try:
                await client.post(
                    f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": reply, "parse_mode": "HTML"},
                    timeout=5
                )
            except Exception as e:
                logger.error(f"Failed to send reply to Telegram chat {chat_id}: {e}")

bot_listener = TelegramBotListener()
