from fastapi import APIRouter

from app.services.trading_service import trading_service

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "database_enabled": trading_service.database_enabled,
        "database_connected": trading_service.database_connected(),
        "telegram_enabled": trading_service.telegram_enabled,
        "market_data_provider": trading_service.market_data_provider,
    }


@router.get("/ready")
async def readiness_check() -> dict[str, object]:
    return trading_service.readiness()
