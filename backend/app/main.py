from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import subprocess
import sys
import asyncio
from datetime import datetime, timezone

from app.api.router import api_router
from app.core.config import PROJECT_ROOT, settings
from app.scheduler.jobs import build_scheduler
from app.alerts.bot_listener import bot_listener
from app.domain.contracts import AlertType


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Ensure database schema is created on startup
    from app.db.base import Base
    from app.db.session import engine
    import app.db.models  # noqa
    Base.metadata.create_all(bind=engine)

    # Playwright scraper microservice is no longer used. We use yfinance directly.
    scraper_proc = None

    scheduler = None
    if settings.start_scheduler:
        scheduler = build_scheduler()
        scheduler.start()
    
    # Start the background Telegram bot polling task
    bot_listener.start()

    # Trigger background ML model training using historical snapshots
    from app.services.trading_service import trading_service
    async def train_ml_model():
        try:
            await asyncio.sleep(5)
            snapshots = await trading_service.get_snapshots()
            from app.engine.ml_model import ml_scoring_model
            await asyncio.to_thread(ml_scoring_model.load_or_train, snapshots)
        except Exception as e:
            import logging
            logging.getLogger("uvicorn").error(f"Error in ML training task: {e}")
            
    asyncio.create_task(train_ml_model())

    # Start the background Breakout Scanner loop
    async def breakout_scanner_loop():
        try:
            await asyncio.sleep(10) # wait for startup
            from app.services.trading_service import trading_service
            from app.engine.breakout_radar import breakout_radar_engine
            from app.domain.contracts import BreakoutStatus
            from app.alerts.telegram import TelegramNotifier
            from app.domain.contracts import AlertMessage
            
            notifier = TelegramNotifier()
            notified_symbols = set()
            import logging
            logger = logging.getLogger("uvicorn")
            logger.info("Started Background Breakout Scanner loop.")
            
            while True:
                from zoneinfo import ZoneInfo
                from datetime import time, datetime, timezone
                
                # Check for market hours
                now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
                is_market_open = True
                if now_ist.weekday() >= 5:
                    is_market_open = False
                elif not (time(9, 15) <= now_ist.time() <= time(15, 30)):
                    is_market_open = False
                    
                if not is_market_open:
                    await asyncio.sleep(300)
                    continue

                try:
                    snapshots = await trading_service.get_snapshots()
                    candidates = await breakout_radar_engine.scan_market(snapshots)
                    
                    # Filter candidates
                    filtered = [
                        c for c in candidates
                        if c.status.value in ("Confirmed Breakout", "Near Breakout")
                        or (c.confidence_score <= 20)
                    ]
                    
                    if filtered:
                        # Check if we have any NEW symbol in this list that we haven't notified today
                        new_symbols = [c for c in filtered if c.symbol not in notified_symbols]
                        
                        if new_symbols:
                            msg = "📊 <b>CURRENT BREAKOUT RADAR</b>\n\n<pre>\n"
                            msg += f"{'SYMBOL':<10}|{'PRICE':<7}|{'STATUS':<6}|{'SCR'}\n"
                            msg += "-" * 31 + "\n"
                            for c in filtered:
                                sym = c.symbol[:10]
                                price = str(round(c.last_price, 1))
                                
                                stat_val = c.status.value
                                if stat_val == "Confirmed Breakout": stat = "BrkOut"
                                elif stat_val == "Near Breakout": stat = "Near"
                                elif c.confidence_score <= 20: stat = "Bear"
                                else: stat = stat_val[:6]
                                
                                score = f"{c.confidence_score}%"
                                msg += f"{sym:<10}|{price:<7}|{stat:<6}|{score:>3}\n"
                                
                                h = round(c.prev_month_high, 1)
                                l = round(c.prev_month_low, 1)
                                msg += f" ↳ H:{h} L:{l}\n"
                                
                                notified_symbols.add(c.symbol)
                                
                            msg += "</pre>"
                                
                            alert = AlertMessage(
                                alert_type=AlertType.BREAKOUT,
                                symbol="RADAR",
                                title="Breakout Radar Table", 
                                message=msg,
                                triggered_at=datetime.now(timezone.utc)
                            )
                            notifier.send(alert)
                                
                    if datetime.now().hour >= 16:
                        notified_symbols.clear()
                        
                except Exception as e:
                    logger.error(f"Error in breakout scanner loop: {e}")
                    
                await asyncio.sleep(300) # Scan every 5 minutes
        except asyncio.CancelledError:
            pass

    scanner_task = asyncio.create_task(breakout_scanner_loop())

    async def outperform_scanner_loop():
        try:
            await asyncio.sleep(20) # wait for startup
            from app.outperform.scoring_engine import generate_dashboard
            from app.alerts.telegram import TelegramNotifier
            from app.domain.contracts import AlertMessage, AlertType
            
            notifier = TelegramNotifier()
            notified_picks_today = set()
            import logging
            logger = logging.getLogger("uvicorn")
            logger.info("Started Background Outperform Scanner loop.")
            
            while True:
                from zoneinfo import ZoneInfo
                from datetime import time, datetime, timezone
                
                # Check for market hours
                now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
                is_market_open = True
                if now_ist.weekday() >= 5:
                    is_market_open = False
                elif not (time(9, 15) <= now_ist.time() <= time(15, 30)):
                    is_market_open = False
                    
                if not is_market_open:
                    await asyncio.sleep(300)
                    continue

                try:
                    dashboard = await generate_dashboard()
                    top_picks = dashboard.top_picks[:3] # Top 3 picks
                    
                    if top_picks:
                        # Only notify if the #1 pick is new, to avoid spamming every 5 mins
                        top_symbol = top_picks[0].symbol
                        if top_symbol not in notified_picks_today:
                            msg = "🚀 <b>OUTPERFORM TODAY - TOP PICKS</b>\n\n<pre>\n"
                            msg += f"{'SYMBOL':<10}|{'SCORE':<5}|{'BIAS':<5}\n"
                            msg += "-" * 22 + "\n"
                            for p in top_picks:
                                sym = p.symbol[:10]
                                score = str(p.overall_score)
                                bias = p.bias[:5]
                                msg += f"{sym:<10}|{score:<5}|{bias:<5}\n"
                            msg += "</pre>\n"
                            msg += f"<i>Market Health: {dashboard.market_health.sentiment} ({dashboard.market_health.overall_market_score}/100)</i>"
                            
                            alert = AlertMessage(
                                alert_type=AlertType.PORTFOLIO_SUMMARY,
                                symbol="OUTPERFORM",
                                title="Top AI Picks", 
                                message=msg,
                                triggered_at=datetime.now(timezone.utc)
                            )
                            notifier.send(alert)
                            notified_picks_today.add(top_symbol)
                            
                    if datetime.now().hour >= 16:
                        notified_picks_today.clear()
                        
                except Exception as e:
                    logger.error(f"Error in outperform scanner loop: {e}")
                    
                await asyncio.sleep(3600) # Scan every 1 hour for new top picks
        except asyncio.CancelledError:
            pass

    outperform_task = asyncio.create_task(outperform_scanner_loop())

    try:
        yield
    finally:
        # Stop the background Telegram bot polling task
        bot_listener.stop()
        scanner_task.cancel()
        if scheduler and scheduler.running:
            scheduler.shutdown()
        # Terminate the scraper microservice
        # if scraper_proc:
        #     scraper_proc.terminate()
        # scraper_proc.wait()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api")
    dashboard_dir = PROJECT_ROOT / "frontend" / "dashboard" / "public"
    
    @app.get("/breakout-radar")
    async def breakout_radar_page():
        from fastapi.responses import FileResponse
        return FileResponse(dashboard_dir / "index.html")
        
    @app.get("/")
    async def root_page():
        from fastapi.responses import FileResponse
        response = FileResponse(dashboard_dir / "index.html")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    if dashboard_dir.exists():
        app.mount("/", StaticFiles(directory=dashboard_dir, html=True), name="dashboard")
    return app


app = create_app()
# Trigger reload
