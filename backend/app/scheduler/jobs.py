from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.services.trading_service import trading_service


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    
    # Existing 15-min market scanner
    scheduler.add_job(
        trading_service.run_scan,
        "interval",
        minutes=settings.market_scan_interval_minutes,
        id="market_scan",
        replace_existing=True,
    )
    
    # New Daily EOD Bhavcopy Fetch (Runs strictly Monday-Friday at 6:30 PM IST)
    from app.collectors.nse.bhavcopy_scraper import fetch_latest_bhavcopy
    scheduler.add_job(
        fetch_latest_bhavcopy,
        "cron",
        day_of_week="mon-fri",
        hour=18,
        minute=30,
        id="bhavcopy_daily_fetch",
        replace_existing=True,
    )
    
    return scheduler

