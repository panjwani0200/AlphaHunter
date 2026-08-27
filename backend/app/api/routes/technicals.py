from fastapi import APIRouter, Path

from app.domain.contracts import TechnicalAnalysis
from app.engine.technicals import analyze_technicals
from app.services.trading_service import trading_service

router = APIRouter(prefix="/technicals")


@router.get("/{symbol}", response_model=TechnicalAnalysis)
def get_technicals(symbol: str = Path(..., min_length=1, max_length=32)) -> TechnicalAnalysis:
    """Full technical analysis for any tracked symbol."""
    snapshot = trading_service._snapshot_for(symbol.upper())
    return analyze_technicals(snapshot.symbol, snapshot.candles)
