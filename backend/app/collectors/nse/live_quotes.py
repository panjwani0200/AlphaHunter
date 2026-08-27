from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from app.collectors.nse.client import NseClient
from app.collectors.market_data.demo import SECTORS
from app.domain.contracts import LiveQuote


# F&O symbols that also have index endpoints
INDEX_SYMBOLS = {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX"}


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int | None = None) -> int | None:
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return default


def parse_nse_quote(symbol: str, raw: dict[str, Any]) -> LiveQuote:
    """
    Parse a raw NSE /api/quote-equity or /api/quote-derivatives response
    into a LiveQuote domain model.

    NSE equity quote shape (simplified):
    {
        "priceInfo": {
            "lastPrice": 2850.5,
            "previousClose": 2840.0,
            "change": 10.5,
            "pChange": 0.37,
            "vwap": 2845.0,
            "open": 2842.0,
            "intraDayHighLow": { "max": 2865, "min": 2835 },
            "weekHighLow": { "max": 3200, "min": 2100 },
            "upperCP": 3124.0,
            "lowerCP": 2556.0
        },
        "marketDeptOrderBook": {
            "totalBuyQuantity": 50000,
            "totalSellQuantity": 30000
        },
        "industryInfo": { "sector": "Energy", ... }
    }
    """
    price_info = raw.get("priceInfo", {})
    depth = raw.get("marketDeptOrderBook", {})
    industry = raw.get("industryInfo", {})
    intra = price_info.get("intraDayHighLow", {})
    week = price_info.get("weekHighLow", {})

    last_price = _safe_float(price_info.get("lastPrice")) or 0.0
    previous_close = _safe_float(price_info.get("previousClose")) or last_price
    change = _safe_float(price_info.get("change")) or (last_price - previous_close)
    change_percent = _safe_float(price_info.get("pChange")) or 0.0

    # Sector: prefer NSE response, fall back to local sector map
    sector = (
        str(industry.get("sector", "")).strip()
        or str(industry.get("macro", "")).strip()
        or SECTORS.get(symbol.upper(), "Unknown")
    )

    return LiveQuote(
        symbol=symbol.upper(),
        observed_at=datetime.now(timezone.utc),
        last_price=last_price,
        previous_close=previous_close,
        change=change,
        change_percent=change_percent,
        open=_safe_float(price_info.get("open")),
        high=_safe_float(intra.get("max")),
        low=_safe_float(intra.get("min")),
        vwap=_safe_float(price_info.get("vwap")),
        volume=_safe_int(depth.get("totalSellQuantity")),  # proxy — NSE doesn't expose total vol here
        total_buy_quantity=_safe_int(depth.get("totalBuyQuantity")),
        total_sell_quantity=_safe_int(depth.get("totalSellQuantity")),
        upper_circuit=_safe_float(price_info.get("upperCP")),
        lower_circuit=_safe_float(price_info.get("lowerCP")),
        week52_high=_safe_float(week.get("max")),
        week52_low=_safe_float(week.get("min")),
        sector=sector,
        source="nse_live",
    )


class NseLiveQuoteCollector:
    """
    Fetches real-time equity quotes from nseindia.com.

    - Results are cached in-process for `cache_ttl_seconds` to respect NSE rate limits.
    - On any NSE error the last cached value is returned; if no cache exists, raises RuntimeError.
    - All requests go through the shared NseClient (session priming + rate limiter).
    """

    def __init__(self, client: NseClient | None = None, cache_ttl_seconds: int = 60) -> None:
        self._client = client or NseClient()
        self._cache_ttl = cache_ttl_seconds
        self._cache: dict[str, tuple[float, LiveQuote]] = {}   # symbol → (timestamp, quote)

    def quote_for(self, symbol: str) -> LiveQuote:
        """Return a live quote, using cache if fresh enough."""
        upper = symbol.upper()
        cached_at, cached_quote = self._cache.get(upper, (0.0, None))  # type: ignore[assignment]
        if cached_quote and (time.monotonic() - cached_at) < self._cache_ttl:
            return cached_quote

        try:
            raw = self._client.equity_quote(upper)
            quote = parse_nse_quote(upper, raw)
            self._cache[upper] = (time.monotonic(), quote)
            return quote
        except Exception as exc:
            if cached_quote:
                # Return stale cache rather than crash
                return cached_quote
            raise RuntimeError(f"NSE live quote failed for {upper}: {exc}") from exc

    def quote_all(self, symbols: list[str]) -> list[LiveQuote]:
        """Fetch quotes for multiple symbols. Skips errors individually."""
        results: list[LiveQuote] = []
        for symbol in symbols:
            try:
                results.append(self.quote_for(symbol))
            except RuntimeError:
                pass
        return results

    def invalidate(self, symbol: str | None = None) -> None:
        """Clear cache for one symbol or all symbols."""
        if symbol:
            self._cache.pop(symbol.upper(), None)
        else:
            self._cache.clear()
