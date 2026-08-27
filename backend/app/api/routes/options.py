from fastapi import APIRouter, Path, Query, HTTPException
from datetime import date
from app.domain.contracts import OptionChainFull, OptionGreeks
from app.services.trading_service import trading_service

router = APIRouter(prefix="/options")


@router.get("/chain/{symbol}", response_model=OptionChainFull)
async def get_option_chain(
    symbol: str = Path(..., min_length=1, max_length=32, description="NSE symbol e.g. NIFTY, RELIANCE"),
    expiry: date | None = Query(default=None, description="Expiry date (YYYY-MM-DD). Defaults to nearest expiry."),
) -> OptionChainFull:
    """
    Full CE/PE options chain for a symbol.
    - Uses live NSE data when `NSE_OPTIONS_CHAIN_ENABLED=true`
    - Falls back to synthetic demo chain otherwise (always returns data)
    """
    try:
        return await trading_service.get_option_chain(symbol.upper(), expiry=expiry)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/chain/{symbol}/expiries", response_model=list[date])
async def get_option_expiries(
    symbol: str = Path(..., min_length=1, max_length=32),
) -> list[date]:
    """Available option expiry dates for a symbol."""
    try:
        return await trading_service.get_option_expiries(symbol.upper())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/max-pain/{symbol}")
async def get_max_pain(
    symbol: str = Path(..., min_length=1, max_length=32),
    expiry: date | None = Query(default=None),
) -> dict:
    """Max pain level and PCR for a symbol."""
    try:
        chain = await trading_service.get_option_chain(symbol.upper(), expiry=expiry)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "symbol": chain.symbol,
        "underlying_price": chain.underlying_price,
        "expiry_date": chain.expiry_date,
        "max_pain": chain.max_pain,
        "pcr": chain.pcr,
        "atm_iv": chain.atm_iv,
        "atm_strike": chain.atm_strike,
        "max_call_oi_strike": chain.max_call_oi_strike,
        "max_put_oi_strike": chain.max_put_oi_strike,
        "total_ce_oi": chain.total_ce_oi,
        "total_pe_oi": chain.total_pe_oi,
        "source": chain.source,
    }


@router.get("/greeks/{symbol}", response_model=OptionGreeks)
def get_option_greeks(
    symbol: str = Path(..., min_length=1, max_length=32),
    strike: float = Query(...),
    expiry_days: int = Query(default=30)
) -> OptionGreeks:
    """Black-Scholes greeks for an option."""
    return trading_service.get_option_greeks(symbol.upper(), strike, expiry_days)
