from fastapi import APIRouter

from app.domain.contracts import AlertMessage, BacktestMetrics
from app.services.trading_service import trading_service

router = APIRouter(prefix="/reports")


@router.post("/daily", response_model=AlertMessage)
async def daily_report() -> AlertMessage:
    return await trading_service.daily_report()


@router.post("/backtest", response_model=BacktestMetrics)
async def backtest() -> BacktestMetrics:
    return trading_service.backtest()

