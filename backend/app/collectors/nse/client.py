from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.utils.rate_limiter import SlidingWindowRateLimiter


class NseClient:
    base_url = "https://www.nseindia.com"

    def __init__(self) -> None:
        # Timeout set from settings to avoid premature fallback
        self._client = httpx.Client(base_url="http://127.0.0.1:8001", timeout=float(settings.nse_request_timeout_seconds))
        self._limiter = SlidingWindowRateLimiter(settings.nse_rate_limit_per_minute)

    def close(self) -> None:
        self._client.close()

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._get_json_with_retry(path, params)

    @retry(wait=wait_exponential(multiplier=1, min=0.5, max=2), stop=stop_after_attempt(2), reraise=True)
    def _get_json_with_retry(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._limiter.wait()
        url = path
        if params:
            url = f"{path}?{urlencode(params)}"

        try:
            response = self._client.get("/fetch", params={"url": url})
            response.raise_for_status()
            res_data = response.json()
            if not res_data.get("ok"):
                raise RuntimeError(res_data.get("error"))
            return json.loads(res_data["data"])
        except Exception as e:
            raise RuntimeError(f"NSE request failed: {e}") from e

    def get_text(self, path: str, params: dict[str, Any] | None = None) -> str:
        return self._get_text_with_retry(path, params)

    @retry(wait=wait_exponential(multiplier=1, min=0.5, max=2), stop=stop_after_attempt(2), reraise=True)
    def _get_text_with_retry(self, path: str, params: dict[str, Any] | None = None) -> str:
        self._limiter.wait()
        url = path
        if params:
            url = f"{path}?{urlencode(params)}"

        try:
            response = self._client.get("/fetch", params={"url": url})
            response.raise_for_status()
            res_data = response.json()
            if not res_data.get("ok"):
                raise RuntimeError(res_data.get("error"))
            return res_data["data"]
        except Exception as e:
            raise RuntimeError(f"NSE request failed: {e}") from e

    def equity_quote(self, symbol: str) -> dict[str, Any]:
        return self.get_json("/api/quote-equity", {"symbol": symbol.upper()})

    def option_chain_contract_info(self, symbol: str) -> dict[str, Any]:
        return self.get_json("/api/option-chain-contract-info", {"symbol": symbol.upper()})

    def option_chain(self, symbol: str, expiry_str: str, is_index: bool = False) -> dict[str, Any]:
        type_param = "Indices" if is_index else "Equities"
        return self.get_json("/api/option-chain-v3", {"type": type_param, "symbol": symbol.upper(), "expiry": expiry_str})

    def security_archives(
        self,
        symbol: str,
        from_date: str,
        to_date: str,
        series: str = "ALL",
        csv: bool = True,
    ) -> str | dict[str, Any]:
        params: dict[str, Any] = {
            "from": from_date,
            "to": to_date,
            "symbol": symbol.upper(),
            "dataType": "priceVolumeDeliverable",
            "series": series.upper(),
        }
        if csv:
            params["csv"] = "true"
            return self.get_text("/api/historical/securityArchives", params=params)
        return self.get_json("/api/historical/securityArchives", params=params)
