from __future__ import annotations

import csv
from datetime import date, datetime
from io import StringIO
from typing import Any

from app.collectors.nse.client import NseClient
from app.domain.contracts import SecurityArchiveRecord


class NseSecurityArchiveCollector:
    def __init__(self, client: NseClient | None = None) -> None:
        self.client = client or NseClient()

    def fetch(
        self,
        symbol: str,
        from_date: date,
        to_date: date,
        series: str = "ALL",
    ) -> list[SecurityArchiveRecord]:
        from_value = from_date.strftime("%d-%m-%Y")
        to_value = to_date.strftime("%d-%m-%Y")

        try:
            csv_text = self.client.security_archives(
                symbol=symbol,
                from_date=from_value,
                to_date=to_value,
                series=series,
                csv=True,
            )
            if isinstance(csv_text, str):
                records = self._parse_csv(csv_text)
                if records:
                    return records
        except Exception:
            pass

        payload = self.client.security_archives(
            symbol=symbol,
            from_date=from_value,
            to_date=to_value,
            series=series,
            csv=False,
        )
        if not isinstance(payload, dict):
            return []
        return self._parse_json(payload)

    def _parse_csv(self, csv_text: str) -> list[SecurityArchiveRecord]:
        cleaned = csv_text.strip().lstrip("\ufeff")
        if not cleaned:
            return []

        reader = csv.DictReader(StringIO(cleaned))
        return [self._record_from_row(row) for row in reader if self._has_symbol(row)]

    def _parse_json(self, payload: dict[str, Any]) -> list[SecurityArchiveRecord]:
        rows = payload.get("data") or payload.get("securityArchives") or []
        if not isinstance(rows, list):
            return []
        return [self._record_from_row(row) for row in rows if isinstance(row, dict) and self._has_symbol(row)]

    def _record_from_row(self, row: dict[str, Any]) -> SecurityArchiveRecord:
        normalized = {self._normalize_key(key): value for key, value in row.items()}
        return SecurityArchiveRecord(
            symbol=str(self._pick(normalized, "symbol", "ch_symbol")).strip().upper(),
            series=str(self._pick(normalized, "series", "ch_series", default="EQ")).strip().upper(),
            trade_date=self._date(self._pick(normalized, "date", "timestamp", "ch_timestamp")),
            previous_close=self._float(
                self._pick(normalized, "prev_close", "previous_close", "ch_previous_cls_price")
            ),
            open_price=self._float(self._pick(normalized, "open_price", "open", "ch_opening_price")),
            high_price=self._float(self._pick(normalized, "high_price", "high", "ch_trade_high_price")),
            low_price=self._float(self._pick(normalized, "low_price", "low", "ch_trade_low_price")),
            last_price=self._float(
                self._pick(normalized, "last_price", "last_traded_price", "ch_last_traded_price")
            ),
            close_price=self._float(self._pick(normalized, "close_price", "close", "ch_closing_price")),
            vwap=self._float(self._pick(normalized, "vwap", "ca_vwap")),
            total_traded_quantity=self._int(
                self._pick(normalized, "total_traded_quantity", "tottrdqty", "ch_tot_traded_qty")
            ),
            turnover=self._float(
                self._pick(normalized, "turnover", "total_traded_value", "tottrdval", "ch_turnover")
            ),
            number_of_trades=self._int(
                self._pick(normalized, "no_of_trades", "number_of_trades", "totaltrades", "m_trades")
            ),
            deliverable_quantity=self._int(
                self._pick(normalized, "deliverable_qty", "deliveryqty", "cop_deliv_qty")
            ),
            delivery_to_traded_percent=self._float(
                self._pick(
                    normalized,
                    "dly_qt_to_traded_qty",
                    "deliverable_percent",
                    "deliveryper",
                    "cop_deliv_perc",
                )
            ),
            source="nse_security_archives",
        )

    def _has_symbol(self, row: dict[str, Any]) -> bool:
        normalized_keys = {self._normalize_key(key) for key in row}
        return bool({"symbol", "ch_symbol"} & normalized_keys)

    def _normalize_key(self, key: str) -> str:
        return (
            key.strip()
            .lower()
            .replace("₹", "")
            .replace("%", "")
            .replace(".", "")
            .replace("-", "_")
            .replace("/", "_")
            .replace(" ", "_")
            .replace("__", "_")
            .strip("_")
        )

    def _pick(self, row: dict[str, Any], *keys: str, default: Any = None) -> Any:
        for key in keys:
            if key in row and row[key] not in {None, "", "-"}:
                return row[key]
        return default

    def _date(self, value: Any) -> date:
        text = str(value).strip()
        for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d", "%d-%B-%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Unsupported NSE archive date: {text}")

    def _float(self, value: Any) -> float | None:
        if value in {None, "", "-"}:
            return None
        return float(str(value).replace(",", "").strip())

    def _int(self, value: Any) -> int | None:
        if value in {None, "", "-"}:
            return None
        return int(float(str(value).replace(",", "").strip()))
