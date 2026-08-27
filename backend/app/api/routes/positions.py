from fastapi import APIRouter

from app.domain.contracts import (
    PositionInput, PositionState, PortfolioRisk, 
    PositionHealth, ThesisValidationResult, PerformanceMetrics
)
from app.services.trading_service import trading_service

router = APIRouter(prefix="/positions")


@router.get("", response_model=list[PositionState])
async def list_positions() -> list[PositionState]:
    return await trading_service.list_positions()
@router.delete("/{position_id}", status_code=204)
async def remove_position(position_id: str):
    trading_service.remove_position(position_id)
    return None


@router.post("", response_model=PositionState)
async def add_position(position: PositionInput) -> PositionState:
    return await trading_service.add_position(position)


@router.post("/evaluate", response_model=list[PositionState])
async def evaluate_positions() -> list[PositionState]:
    return await trading_service.evaluate_positions()


@router.get("/portfolio/risk", response_model=PortfolioRisk)
async def portfolio_risk() -> PortfolioRisk:
    return await trading_service.get_portfolio_risk()


@router.get("/portfolio/performance", response_model=PerformanceMetrics)
async def portfolio_performance() -> PerformanceMetrics:
    return trading_service.get_performance_metrics()


@router.get("/{symbol}/health", response_model=PositionHealth)
async def position_health(symbol: str, instrument: str = "", entry: float = 0.0, current: float = 0.0) -> PositionHealth:
    return await trading_service.get_position_health(symbol, instrument, entry, current)


@router.post("/{symbol}/thesis", response_model=ThesisValidationResult)
async def validate_thesis(symbol: str, entry: float, thesis: dict) -> ThesisValidationResult:
    return await trading_service.validate_thesis(symbol, entry, thesis)

