from fastapi import APIRouter

from app.api.routes.alerts import router as alerts_router
from app.api.routes.market import router as market_router
from app.api.routes.exports import router as exports_router
from app.api.routes.positions import router as positions_router
from app.api.routes.reports import router as reports_router
from app.api.routes.scanner import router as scanner_router
from app.api.routes.health import router as health_router
from app.api.routes.technicals import router as technicals_router
from app.api.routes.options import router as options_router
from app.api.routes.backtest import router as backtest_router
from app.api.routes.strategy import router as strategy_router
from app.api.routes.assistant import router as assistant_router
from app.api.routes.breakout_radar import router as breakout_radar_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(market_router, tags=["market"])
api_router.include_router(exports_router, tags=["exports"])
api_router.include_router(scanner_router, tags=["scanner"])
api_router.include_router(positions_router, tags=["positions"])
api_router.include_router(alerts_router, tags=["alerts"])
api_router.include_router(reports_router, tags=["reports"])
api_router.include_router(technicals_router, tags=["technicals"])
api_router.include_router(options_router, tags=["options"])
api_router.include_router(backtest_router, tags=["backtest"])
api_router.include_router(strategy_router, tags=["strategy"])
api_router.include_router(assistant_router, tags=["assistant"])
api_router.include_router(breakout_radar_router, tags=["breakout_radar"])

from app.outperform.router import router as outperform_router
api_router.include_router(outperform_router, prefix="/outperform", tags=["outperform"])



