from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import pandas as pd

from app.domain.contracts import MarketCandle, MarketSnapshot


class YahooMarketDataCollector:
    def __init__(self) -> None:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError("Install yfinance to use YahooMarketDataCollector") from exc
        self._yf: Any = yf

    def snapshot_for(self, symbol: str, period: str = "1y") -> MarketSnapshot:
        sym_upper = symbol.upper()
        if sym_upper == "NIFTY":
            ticker = "^NSEI"
        elif sym_upper == "BANKNIFTY":
            ticker = "^NSEBANK"
        else:
            ticker = sym_upper if sym_upper.endswith(".NS") else f"{sym_upper}.NS"
        frame = self._yf.download(ticker, period=period, progress=False, auto_adjust=False)
        if frame.empty:
            raise RuntimeError(f"No Yahoo data returned for {ticker}")

        candles: list[MarketCandle] = []
        for index, row in frame.iterrows():
            close_val = row.get("Close")
            if isinstance(close_val, pd.Series):
                close_val = close_val.iloc[0]
            if pd.isna(close_val):
                continue

            open_val = row.get("Open")
            if isinstance(open_val, pd.Series):
                open_val = open_val.iloc[0]

            high_val = row.get("High")
            if isinstance(high_val, pd.Series):
                high_val = high_val.iloc[0]

            low_val = row.get("Low")
            if isinstance(low_val, pd.Series):
                low_val = low_val.iloc[0]

            vol_val = row.get("Volume")
            if isinstance(vol_val, pd.Series):
                vol_val = vol_val.iloc[0]

            observed_at = index.to_pydatetime().replace(tzinfo=timezone.utc)
            candles.append(
                MarketCandle(
                    symbol=symbol.upper().replace(".NS", ""),
                    observed_at=observed_at,
                    open=float(open_val),
                    high=float(high_val),
                    low=float(low_val),
                    close=float(close_val),
                    volume=int(vol_val or 0),
                )
            )

        if not candles:
            raise RuntimeError(f"No candles returned after filtering NaNs for {ticker}")

        latest = candles[-1]
        previous = candles[-2] if len(candles) > 1 else latest
        average_volume = int(sum(candle.volume for candle in candles[-20:]) / min(20, len(candles)))
        from app.collectors.market_data.demo import SECTORS
        return MarketSnapshot(
            symbol=symbol.upper().replace(".NS", ""),
            observed_at=datetime.now(timezone.utc),
            last_price=latest.close,
            previous_close=previous.close,
            change_percent=round(((latest.close - previous.close) / previous.close) * 100, 2),
            volume=latest.volume,
            average_volume_20d=average_volume,
            candles=candles,
            sector=SECTORS.get(symbol.upper().replace(".NS", ""), "Unknown"),
            source="yfinance",
        )

    def intraday_for(self, symbol: str, interval: str = "5m", period: str = "5d") -> list[MarketCandle]:
        sym_upper = symbol.upper()
        if sym_upper == "NIFTY":
            ticker = "^NSEI"
        elif sym_upper == "BANKNIFTY":
            ticker = "^NSEBANK"
        else:
            ticker = sym_upper if sym_upper.endswith(".NS") else f"{sym_upper}.NS"
        
        frame = self._yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
        if frame.empty:
            raise RuntimeError(f"No Yahoo intraday data returned for {ticker} (interval={interval}, period={period})")

        candles: list[MarketCandle] = []
        for index, row in frame.iterrows():
            close_val = row.get("Close")
            if isinstance(close_val, pd.Series):
                close_val = close_val.iloc[0]
            if pd.isna(close_val):
                continue

            open_val = row.get("Open")
            if isinstance(open_val, pd.Series):
                open_val = open_val.iloc[0]

            high_val = row.get("High")
            if isinstance(high_val, pd.Series):
                high_val = high_val.iloc[0]

            low_val = row.get("Low")
            if isinstance(low_val, pd.Series):
                low_val = low_val.iloc[0]

            vol_val = row.get("Volume")
            if isinstance(vol_val, pd.Series):
                vol_val = vol_val.iloc[0]

            observed_at = index.to_pydatetime().replace(tzinfo=timezone.utc)
            candles.append(
                MarketCandle(
                    symbol=symbol.upper().replace(".NS", ""),
                    observed_at=observed_at,
                    open=float(open_val),
                    high=float(high_val),
                    low=float(low_val),
                    close=float(close_val),
                    volume=int(vol_val or 0),
                )
            )

        if not candles:
            raise RuntimeError(f"No valid intraday candles returned after filtering NaNs for {ticker}")
            
        return candles

    def collect_market_snapshots(self, symbols: list[str], period: str = "1y") -> list[MarketSnapshot]:
        equity_symbols = [s for s in symbols if "NIFTY" not in s]
        tickers = [s.upper() if s.upper().endswith(".NS") else f"{s.upper()}.NS" for s in equity_symbols]
        
        try:
            df = self._yf.download(tickers, period=period, progress=False, group_by="ticker", auto_adjust=False)
        except Exception as e:
            raise RuntimeError(f"Yahoo batch download failed: {e}")
            
        results: list[MarketSnapshot] = []
        for symbol in equity_symbols:
            ticker = symbol.upper() if symbol.upper().endswith(".NS") else f"{symbol.upper()}.NS"
            try:
                if len(tickers) == 1:
                    frame = df
                else:
                    frame = df[ticker]
                
                if frame.empty:
                    continue
                    
                candles: list[MarketCandle] = []
                for index, row in frame.iterrows():
                    close_val = row.get("Close")
                    if isinstance(close_val, pd.Series):
                        close_val = close_val.iloc[0]
                    if pd.isna(close_val):
                        continue

                    open_val = row.get("Open")
                    if isinstance(open_val, pd.Series):
                        open_val = open_val.iloc[0]

                    high_val = row.get("High")
                    if isinstance(high_val, pd.Series):
                        high_val = high_val.iloc[0]

                    low_val = row.get("Low")
                    if isinstance(low_val, pd.Series):
                        low_val = low_val.iloc[0]

                    vol_val = row.get("Volume")
                    if isinstance(vol_val, pd.Series):
                        vol_val = vol_val.iloc[0]

                    observed_at = index.to_pydatetime().replace(tzinfo=timezone.utc)
                    candles.append(
                        MarketCandle(
                            symbol=symbol,
                            observed_at=observed_at,
                            open=float(open_val),
                            high=float(high_val),
                            low=float(low_val),
                            close=float(close_val),
                            volume=int(vol_val or 0),
                        )
                    )
                
                if not candles:
                    continue

                latest = candles[-1]
                previous = candles[-2] if len(candles) > 1 else latest
                average_volume = int(sum(candle.volume for candle in candles[-20:]) / min(20, len(candles)))
                
                from app.collectors.market_data.demo import SECTORS
                results.append(MarketSnapshot(
                    symbol=symbol,
                    observed_at=datetime.now(timezone.utc),
                    last_price=latest.close,
                    previous_close=previous.close,
                    change_percent=round(((latest.close - previous.close) / previous.close) * 100, 2),
                    volume=latest.volume,
                    average_volume_20d=average_volume,
                    candles=candles,
                    sector=SECTORS.get(symbol, "Unknown"),
                    source="yfinance",
                ))
            except Exception:
                pass
        return results

