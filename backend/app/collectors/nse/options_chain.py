from __future__ import annotations

import time
from datetime import date, datetime, timezone
from typing import Any

from app.collectors.nse.client import NseClient
from app.domain.contracts import OptionChainFull, OptionStrike


INDEX_SYMBOLS = {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX"}


def _safe_float(value: Any) -> float | None:
    try:
        v = str(value).replace(",", "").strip()
        return float(v) if v and v != "-" else None
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        v = str(value).replace(",", "").strip()
        return int(float(v)) if v and v != "-" else None
    except (TypeError, ValueError):
        return None


def _parse_date(text: str) -> date | None:
    """Parse NSE expiry date strings like '26-Jun-2025'."""
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(text).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _compute_max_pain(strikes: list[OptionStrike]) -> float | None:
    """
    Max pain = the strike price at which the total value of in-the-money
    options (both CE and PE) is minimised for buyers.

    Simple approximation: for each candidate strike S,
    sum up (S - K) * CE_OI for all calls where K < S,
    and (K - S) * PE_OI for all puts where K > S.
    The minimum of this total = max pain strike.
    """
    if not strikes:
        return None
    strike_prices = [s.strike_price for s in strikes]
    best_strike = None
    best_value = float("inf")

    for candidate in strike_prices:
        total = 0
        for s in strikes:
            # ITM calls: K < S, call buyers lose if spot < K
            if s.strike_price < candidate and s.ce_oi:
                total += (candidate - s.strike_price) * s.ce_oi
            # ITM puts: K > S, put buyers lose if spot > K
            if s.strike_price > candidate and s.pe_oi:
                total += (s.strike_price - candidate) * s.pe_oi
        if total < best_value:
            best_value = total
            best_strike = candidate
    return best_strike


def parse_option_chain(symbol: str, raw: dict[str, Any], expiry_filter: date | None = None) -> OptionChainFull:
    """
    Parse the raw NSE /api/option-chain-equities or /api/option-chain-indices
    response into OptionChainFull.

    NSE shape:
    {
      "records": {
        "underlyingValue": 24850.5,
        "expiryDates": ["26-Jun-2025", "31-Jul-2025", ...],
        "data": [
          {
            "strikePrice": 24000,
            "expiryDate": "26-Jun-2025",
            "CE": { "openInterest": 12000, "changeinOpenInterest": 500, "lastPrice": 855, "impliedVolatility": 22.5, "totalTradedVolume": 3400, "bidprice": 854, "askPrice": 856, "pChange": 1.2 },
            "PE": { ... }
          }
        ]
      },
      "filtered": { "data": [...] }  # filtered = near ATM, use records.data for full chain
    }
    """
    records = raw.get("records", {})
    underlying_price: float = _safe_float(records.get("underlyingValue")) or 0.0
    now = datetime.now(timezone.utc)

    # Parse available expiry dates
    raw_expiries = records.get("expiryDates", [])
    expiry_dates: list[date] = []
    for ed in raw_expiries:
        parsed = _parse_date(str(ed))
        if parsed:
            expiry_dates.append(parsed)

    # Choose expiry: use filter or nearest upcoming
    target_expiry: date | None = expiry_filter
    if not target_expiry and expiry_dates:
        today = datetime.now(timezone.utc).date()
        upcoming = [e for e in expiry_dates if e >= today]
        target_expiry = upcoming[0] if upcoming else expiry_dates[0]

    # Parse strike rows
    all_rows = records.get("data", [])
    strike_map: dict[float, OptionStrike] = {}

    for row in all_rows:
        row_expiry_text = str(row.get("expiryDate") or row.get("expiryDates") or "").strip()
        row_expiry = _parse_date(row_expiry_text)
        if target_expiry and row_expiry != target_expiry:
            continue

        strike_price = _safe_float(row.get("strikePrice"))
        if strike_price is None:
            continue

        ce_data = row.get("CE", {}) or {}
        pe_data = row.get("PE", {}) or {}

        # Derived: per-strike PCR
        ce_oi = _safe_int(ce_data.get("openInterest"))
        pe_oi = _safe_int(pe_data.get("openInterest"))
        pcr_at_strike: float | None = None
        if ce_oi and pe_oi and ce_oi > 0:
            pcr_at_strike = round(pe_oi / ce_oi, 3)

        ce_change_oi = _safe_int(ce_data.get("changeinOpenInterest"))
        pe_change_oi = _safe_int(pe_data.get("changeinOpenInterest"))
        net_oi_pressure: int | None = None
        if ce_change_oi is not None and pe_change_oi is not None:
            net_oi_pressure = ce_change_oi - pe_change_oi

        strike_map[strike_price] = OptionStrike(
            strike_price=strike_price,
            expiry_date=target_expiry or (row_expiry or datetime.now(timezone.utc).date()),
            # Call side
            ce_ltp=_safe_float(ce_data.get("lastPrice")),
            ce_oi=ce_oi,
            ce_change_oi=ce_change_oi,
            ce_volume=_safe_int(ce_data.get("totalTradedVolume")),
            ce_iv=_safe_float(ce_data.get("impliedVolatility")),
            ce_bid=_safe_float(ce_data.get("bidprice")),
            ce_ask=_safe_float(ce_data.get("askPrice")),
            ce_change_percent=_safe_float(ce_data.get("pChange")),
            # Put side
            pe_ltp=_safe_float(pe_data.get("lastPrice")),
            pe_oi=pe_oi,
            pe_change_oi=pe_change_oi,
            pe_volume=_safe_int(pe_data.get("totalTradedVolume")),
            pe_iv=_safe_float(pe_data.get("impliedVolatility")),
            pe_bid=_safe_float(pe_data.get("bidprice")),
            pe_ask=_safe_float(pe_data.get("askPrice")),
            pe_change_percent=_safe_float(pe_data.get("pChange")),
            # Derived
            pcr_at_strike=pcr_at_strike,
            net_oi_pressure=net_oi_pressure,
        )

    strikes_sorted = sorted(strike_map.values(), key=lambda s: s.strike_price)

    # Aggregate totals
    total_ce_oi = sum(s.ce_oi for s in strikes_sorted if s.ce_oi) or 0
    total_pe_oi = sum(s.pe_oi for s in strikes_sorted if s.pe_oi) or 0
    total_ce_vol = sum(s.ce_volume for s in strikes_sorted if s.ce_volume) or 0
    total_pe_vol = sum(s.pe_volume for s in strikes_sorted if s.pe_volume) or 0
    pcr = round(total_pe_oi / total_ce_oi, 3) if total_ce_oi > 0 else 1.0

    # Max OI strikes (resistance / support walls)
    max_call_strike: float | None = None
    max_put_strike: float | None = None
    max_call_oi = 0
    max_put_oi = 0
    for s in strikes_sorted:
        if s.ce_oi and s.ce_oi > max_call_oi:
            max_call_oi = s.ce_oi
            max_call_strike = s.strike_price
        if s.pe_oi and s.pe_oi > max_put_oi:
            max_put_oi = s.pe_oi
            max_put_strike = s.strike_price

    # ATM strike (nearest to underlying price)
    atm_strike: float | None = None
    if strikes_sorted and underlying_price > 0:
        atm_strike = min(strikes_sorted, key=lambda s: abs(s.strike_price - underlying_price)).strike_price

    # ATM IV (average of CE IV and PE IV at ATM)
    atm_iv: float | None = None
    if atm_strike is not None:
        atm = strike_map.get(atm_strike)
        if atm:
            ivs = [v for v in [atm.ce_iv, atm.pe_iv] if v is not None]
            atm_iv = round(sum(ivs) / len(ivs), 2) if ivs else None

    # Mark ATM and compute max pain
    max_pain = _compute_max_pain(strikes_sorted)
    for s in strikes_sorted:
        s.is_atm = (s.strike_price == atm_strike)
        s.is_max_pain = (max_pain is not None and s.strike_price == max_pain)

    return OptionChainFull(
        symbol=symbol.upper(),
        observed_at=now,
        underlying_price=underlying_price,
        expiry_date=target_expiry or (expiry_dates[0] if expiry_dates else datetime.now(timezone.utc).date()),
        expiry_dates=expiry_dates,
        pcr=pcr,
        max_pain=max_pain,
        max_call_oi_strike=max_call_strike,
        max_put_oi_strike=max_put_strike,
        total_ce_oi=total_ce_oi,
        total_pe_oi=total_pe_oi,
        total_ce_volume=total_ce_vol,
        total_pe_volume=total_pe_vol,
        atm_iv=atm_iv,
        atm_strike=atm_strike,
        strikes=strikes_sorted,
        source="nse_live",
    )


class NseOptionsChainCollector:
    """
    Fetches and parses live options chain data from nseindia.com.

    - Uses the index endpoint for NIFTY/BANKNIFTY/FINNIFTY
    - Uses the equity endpoint for individual stocks
    - Results are cached per (symbol, expiry) for cache_ttl_seconds
    """

    def __init__(self, client: NseClient | None = None, cache_ttl_seconds: int = 60) -> None:
        self._client = client or NseClient()
        self._cache_ttl = cache_ttl_seconds
        # (symbol, expiry_str) → (timestamp, OptionChainFull)
        self._cache: dict[tuple[str, str], tuple[float, OptionChainFull]] = {}

    def _cache_key(self, symbol: str, expiry: date | None) -> tuple[str, str]:
        return (symbol.upper(), str(expiry) if expiry else "nearest")

    def get_chain(self, symbol: str, expiry: date | None = None) -> OptionChainFull:
        """Return the options chain, from cache if fresh enough."""
        upper = symbol.upper()
        key = self._cache_key(upper, expiry)
        cached_at, cached_chain = self._cache.get(key, (0.0, None))  # type: ignore[assignment]
        if cached_chain and (time.monotonic() - cached_at) < self._cache_ttl:
            return cached_chain

        try:
            is_index = upper in INDEX_SYMBOLS
            
            # 1. Fetch available expiries from contract-info
            contract_info = self._client.option_chain_contract_info(upper)
            raw_expiries = contract_info.get("expiryDates", [])
            
            expiry_dates: list[date] = []
            for ed in raw_expiries:
                parsed = _parse_date(ed)
                if parsed:
                    expiry_dates.append(parsed)
            
            if not expiry_dates:
                raise RuntimeError(f"No expiry dates found in contract info for {upper}")
                
            # 2. Match target expiry
            target_expiry = expiry
            if not target_expiry:
                today = datetime.now(timezone.utc).date()
                upcoming = [e for e in expiry_dates if e >= today]
                target_expiry = upcoming[0] if upcoming else expiry_dates[0]
                
            # Find the string matching target_expiry
            expiry_str = None
            for ed in raw_expiries:
                if _parse_date(ed) == target_expiry:
                    expiry_str = str(ed).strip()
                    break
                    
            if not expiry_str:
                expiry_str = target_expiry.strftime("%d-%b-%Y")
                
            # 3. Fetch v3 chain
            raw = self._client.option_chain(upper, expiry_str=expiry_str, is_index=is_index)
            
            # 4. Parse the chain
            chain = parse_option_chain(upper, raw, expiry_filter=target_expiry)
            if not chain.expiry_dates and expiry_dates:
                chain.expiry_dates = expiry_dates
                
            self._cache[key] = (time.monotonic(), chain)
            return chain
        except Exception as exc:
            if cached_chain:
                return cached_chain
            raise RuntimeError(f"NSE options chain failed for {upper}: {exc}") from exc

    def get_expiries(self, symbol: str) -> list[date]:
        """Return available expiry dates for a symbol (uses contract info directly for speed)."""
        key = self._cache_key(symbol, None)
        _, cached = self._cache.get(key, (0.0, None))  # type: ignore[assignment]
        if cached:
            return cached.expiry_dates
        try:
            contract_info = self._client.option_chain_contract_info(symbol)
            raw_expiries = contract_info.get("expiryDates", [])
            expiry_dates: list[date] = []
            for ed in raw_expiries:
                parsed = _parse_date(ed)
                if parsed:
                    expiry_dates.append(parsed)
            return expiry_dates
        except Exception:
            try:
                chain = self.get_chain(symbol)
                return chain.expiry_dates
            except RuntimeError:
                return []

    def invalidate(self, symbol: str | None = None) -> None:
        if symbol:
            keys_to_del = [k for k in self._cache if k[0] == symbol.upper()]
            for k in keys_to_del:
                del self._cache[k]
        else:
            self._cache.clear()
