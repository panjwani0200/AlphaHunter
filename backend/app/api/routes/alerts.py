from fastapi import APIRouter, Query

from app.domain.contracts import AlertMessage
from app.services.trading_service import trading_service

router = APIRouter(prefix="/alerts")


@router.get("", response_model=list[AlertMessage])
async def list_alerts(limit: int = Query(default=50, ge=1, le=200)) -> list[AlertMessage]:
    return await trading_service.list_alerts(limit=limit)


@router.post("/portfolio-summary", response_model=AlertMessage)
async def portfolio_summary() -> AlertMessage:
    return await trading_service.portfolio_summary()


@router.post("/telegram-test", response_model=AlertMessage)
async def telegram_test() -> AlertMessage:
    return trading_service.telegram_test()
