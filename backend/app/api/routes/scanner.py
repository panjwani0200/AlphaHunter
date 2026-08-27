from fastapi import APIRouter, Query

from app.domain.contracts import ScannerCandidate, TradeCard, ExitSignal
from app.services.trading_service import trading_service

router = APIRouter(prefix="/scanner")


@router.post("/run", response_model=list[ScannerCandidate])
async def run_scanner(limit: int = Query(default=20, ge=1, le=100)) -> list[ScannerCandidate]:
    return await trading_service.run_scan(limit=limit)


@router.get("/latest", response_model=list[ScannerCandidate])
async def latest_scanner_results(
    limit: int = Query(default=20, ge=1, le=100),
    signal: str | None = Query(default=None, description="Filter by signal type: breakout, swing_long, swing_short, reversal, momentum"),
) -> list[ScannerCandidate]:
    results = await trading_service.run_scan(limit=100)
    if signal:
        results = [r for r in results if r.signal_type.value == signal]
    return results[:limit]


@router.get("/symbols", response_model=list[str])
def scanner_symbols() -> list[str]:
    """Returns the list of symbols currently being scanned."""
    return list(trading_service._active_symbols)

@router.post("/symbols/{symbol}")
async def add_scanner_symbol(symbol: str):
    trading_service.add_scan_symbol(symbol)
    return {"ok": True, "message": f"{symbol} added to scanner"}

@router.delete("/symbols/{symbol}")
async def remove_scanner_symbol(symbol: str):
    trading_service.remove_scan_symbol(symbol)
    return {"ok": True, "message": f"{symbol} removed from scanner"}


@router.get("/signals", response_model=list[TradeCard])
async def ai_signal_pro_results() -> list[TradeCard]:
    return await trading_service.get_ai_signals()


@router.get("/exits", response_model=list[ExitSignal])
async def ai_exit_signals() -> list[ExitSignal]:
    return await trading_service.get_exit_signals()
