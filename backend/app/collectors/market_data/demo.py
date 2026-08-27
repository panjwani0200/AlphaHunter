from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from random import Random

from app.domain.contracts import (
    MarketCandle,
    MarketSnapshot,
    OiInterpretation,
    OiSnapshot,
    OptionChainAnalysis,
    OptionLevel,
    SecurityArchiveRecord,
)


DEFAULT_SYMBOLS = [
    'AARTIIND', 'ABB', 'ABBOTINDIA', 'ABCAPITAL', 'ABFRL', 'ACC', 'ADANIENT', 'ADANIPORTS', 'ADANIPOWER', 'ALKEM', 'AMBUJACEM', 'APOLLOHOSP', 'APOLLOTYRE', 'ASHOKLEY', 'ASIANPAINT', 'ASTRAL', 'ATUL', 'AUBANK', 'AUROPHARMA', 'AXISBANK', 'BAJAJ-AUTO', 'BAJAJFINSV', 'BAJFINANCE', 'BALKRISIND', 'BALRAMCHIN', 'BANDHANBNK', 'BANKBARODA', 'BANKNIFTY', 'BATAINDIA', 'BEL', 'BERGEPAINT', 'BHARATFORG', 'BHARTIARTL', 'BHEL', 'BIOCON', 'BOSCHLTD', 'BPCL', 'BRITANNIA', 'BSOFT', 'CANBK', 'CANFINHOME', 'CHAMBLFERT', 'CHOLAFIN', 'CIPLA', 'COALINDIA', 'COFORGE', 'COLPAL', 'CONCOR', 'COROMANDEL', 'CROMPTON', 'CUB', 'CUMMINSIND', 'DABUR', 'DALBHARAT', 'DEEPAKNTR', 'DELTACORP', 'DIVISLAB', 'DIXON', 'DLF', 'DRREDDY', 'EICHERMOT', 'ESCORTS', 'EXIDEIND', 'FEDERALBNK', 'FINNIFTY', 'GAIL', 'GLENMARK', 'GNFC', 'GODREJCP', 'GODREJPROP', 'GRANULES', 'GRASIM', 'GUJGASLTD', 'HAL', 'HAVELLS', 'HCLTECH', 'HDFCAMC', 'HDFCBANK', 'HDFCLIFE', 'HEROMOTOCO', 'HINDALCO', 'HINDCOPPER', 'HINDPETRO', 'HINDUNILVR', 'ICICIBANK', 'ICICIGI', 'ICICIPRULI', 'IDEA', 'IDFCFIRSTB', 'IEX', 'IGL', 'INDHOTEL', 'INDIACEM', 'INDIAMART', 'INDIGO', 'INDUSINDBK', 'INDUSTOWER', 'INFY', 'INTELLECT', 'IOC', 'IPCALAB', 'IRCTC', 'ITC', 'JINDALSTEL', 'JKCEMENT', 'JSWSTEEL', 'JUBLFOOD', 'KOTAKBANK', 'LALPATHLAB', 'LAURUSLABS', 'LICHSGFIN', 'LT', 'LTTS', 'LUPIN', 'M&M', 'M&MFIN', 'MANAPPURAM', 'MARICO', 'MARUTI', 'MCX', 'METROPOLIS', 'MFSL', 'MGL', 'MIDCPNIFTY', 'MOTHERSON', 'MPHASIS', 'MRF', 'MUTHOOTFIN', 'NATIONALUM', 'NAUKRI', 'NAVINFLUOR', 'NESTLEIND', 'NIFTY', 'NMDC', 'NTPC', 'OBEROIRLTY', 'OFSS', 'ONGC', 'PAGEIND', 'PERSISTENT', 'PETRONET', 'PFC', 'PIDILITIND', 'PIIND', 'PNB', 'POLICYBZR', 'POLYCAB', 'POWERGRID', 'PVRINOX', 'RAIN', 'RAMCOCEM', 'RBLBANK', 'RECLTD', 'RELIANCE', 'SAIL', 'SBICARD', 'SBILIFE', 'SBIN', 'SHREECEM', 'SHRIRAMFIN', 'SIEMENS', 'SRF', 'SUNTV', 'SUNPHARMA', 'SYNGENE', 'TATACHEM', 'TATACOMM', 'TATACONSUM', 'TATAPOWER', 'TATASTEEL', 'TCS', 'TECHM', 'TITAN', 'TORNTPHARM', 'TRENT', 'TVSMOTOR', 'UBL', 'ULTRACEMCO', 'UPL', 'VEDL', 'VOLTAS', 'WHIRLPOOL', 'WIPRO', 'ZEEL', 'ZYDUSLIFE'
]


SECTORS = {
    "POLICYBZR": "Financial Services",
    "RELIANCE": "Energy",
    "TCS": "IT",
    "HDFCBANK": "Banking",
    "ICICIBANK": "Banking",
    "INFY": "IT",
    "LT": "Capital Goods",
    "SBIN": "Banking",
    "BEL": "Defence",
    "CDSL": "Financial Services",
    "ADANIPOWER": "Power",
    "MCX": "Financial Services",
    "NIFTY": "Index",
    "BANKNIFTY": "Index",
    "ITC": "FMCG",
    "HINDUNILVR": "FMCG",
    "BAJFINANCE": "Financial Services",
    "BHARTIARTL": "Telecom",
    "KOTAKBANK": "Banking",
    "ASIANPAINT": "Consumer Durables",
    "MARUTI": "Automobile",
    "SUNPHARMA": "Healthcare",
    "TITAN": "Consumer Durables",
    "ULTRACEMCO": "Construction Materials",
    "TATAMOTORS": "Automobile",
    "NTPC": "Power",
    "ONGC": "Energy",
    "COALINDIA": "Energy",
    "M&M": "Automobile",
    "BAJAJ-AUTO": "Automobile",
    "TATASTEEL": "Metals",
    "HINDALCO": "Metals",
    "JSWSTEEL": "Metals",
    "GRASIM": "Construction Materials",
    "TECHM": "IT",
    "HCLTECH": "IT",
    "WIPRO": "IT",
    "LTIM": "IT",
    "HAL": "Defence",
    "SWIGGY": "Consumer Services",
    "ETERNAL": "Consumer Services",
    "BHEL": "Capital Goods",
    "TRENT": "Consumer Services",
    "VEDL": "Metals",
    "ADANIENT": "Metals",
}


class DemoMarketDataCollector:
    def __init__(self, symbols: list[str] | None = None) -> None:
        self.symbols = symbols or DEFAULT_SYMBOLS

    def collect_market_snapshots(self) -> list[MarketSnapshot]:
        return [self.snapshot_for(symbol) for symbol in self.symbols]

    def snapshot_for(self, symbol: str) -> MarketSnapshot:
        candles = self.candles_for(symbol)
        latest = candles[-1]
        average_volume = int(sum(candle.volume for candle in candles[-20:]) / 20)
        previous_close = candles[-2].close
        change_percent = ((latest.close - previous_close) / previous_close) * 100
        return MarketSnapshot(
            symbol=symbol.upper(),
            observed_at=latest.observed_at,
            last_price=round(latest.close, 2),
            previous_close=round(previous_close, 2),
            change_percent=round(change_percent, 2),
            volume=latest.volume,
            average_volume_20d=average_volume,
            delivery_percent=round(38 + self._rng(symbol).random() * 28, 2),
            sector=SECTORS.get(symbol.upper(), "Unknown"),
            candles=candles,
            source="demo",
        )

    def candles_for(self, symbol: str, days: int = 240) -> list[MarketCandle]:
        rng = self._rng(symbol)
        base_price = 120 + (abs(hash(symbol)) % 2400)
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        trend = self._trend_for(symbol)
        candles: list[MarketCandle] = []
        previous_close = float(base_price)

        for index in range(days):
            observed_at = now - timedelta(days=days - index)
            seasonal = math.sin(index / 8) * 0.7
            drift = trend + seasonal + rng.uniform(-1.4, 1.6)
            open_price = previous_close * (1 + rng.uniform(-0.006, 0.006))
            close = max(10.0, previous_close * (1 + drift / 100))
            high = max(open_price, close) * (1 + rng.uniform(0.002, 0.018))
            low = min(open_price, close) * (1 - rng.uniform(0.002, 0.018))
            volume_base = 400_000 + (abs(hash(symbol)) % 3_000_000)
            volume = int(volume_base * (1 + abs(drift) / 3 + rng.uniform(-0.2, 0.35)))
            if index == days - 1 and symbol.upper() in {"CDSL", "BEL", "MCX"}:
                close = max(close, max(candle.high for candle in candles[-20:]) * 1.01)
                volume = int(volume * 1.9)
            if index == days - 1 and symbol.upper() == "ADANIPOWER":
                close = min(close, min(candle.low for candle in candles[-20:]) * 0.98)
                volume = int(volume * 2.1)

            candles.append(
                MarketCandle(
                    symbol=symbol.upper(),
                    observed_at=observed_at,
                    open=round(open_price, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=round(close, 2),
                    volume=max(1, volume),
                    previous_close=round(previous_close, 2),
                )
            )
            previous_close = close

        return candles

    def oi_for(self, snapshot: MarketSnapshot) -> OiSnapshot:
        symbol = snapshot.symbol.upper()
        oi_change = 2.0
        interpretation = OiInterpretation.NEUTRAL
        if snapshot.change_percent > 1.5:
            oi_change = 8.0
            interpretation = OiInterpretation.LONG_BUILDUP
        if symbol == "ADANIPOWER" or snapshot.change_percent < -1.5:
            oi_change = 11.0
            interpretation = OiInterpretation.SHORT_BUILDUP
        if snapshot.change_percent > 1.2 and symbol == "SBIN":
            oi_change = -4.0
            interpretation = OiInterpretation.SHORT_COVERING

        return OiSnapshot(
            symbol=symbol,
            observed_at=snapshot.observed_at,
            price_change_percent=snapshot.change_percent,
            oi_change_percent=oi_change,
            open_interest=1_000_000 + abs(hash(symbol)) % 4_000_000,
            interpretation=interpretation,
        )

    def option_chain_for(self, snapshot: MarketSnapshot) -> OptionChainAnalysis:
        price = snapshot.last_price
        step = self._strike_step(price)
        center = round(price / step) * step
        levels: list[OptionLevel] = []
        total_call_oi = 0
        total_put_oi = 0
        for offset in range(-4, 5):
            strike = center + offset * step
            call_oi = int(max(1, 100_000 + offset * 35_000 + abs(hash((snapshot.symbol, offset))) % 180_000))
            put_oi = int(max(1, 120_000 - offset * 32_000 + abs(hash((offset, snapshot.symbol))) % 180_000))
            if snapshot.symbol == "ADANIPOWER" and offset <= 0:
                put_oi = int(put_oi * 0.45)
            total_call_oi += call_oi
            total_put_oi += put_oi
            levels.append(OptionLevel(strike_price=float(strike), call_oi=call_oi, put_oi=put_oi))

        max_call = max(levels, key=lambda level: level.call_oi)
        max_put = max(levels, key=lambda level: level.put_oi)
        support_levels = [level for level in levels if level.strike_price <= price]
        resistance_levels = [level for level in levels if level.strike_price >= price]
        support = max(support_levels, key=lambda level: level.put_oi).strike_price if support_levels else None
        resistance = (
            max(resistance_levels, key=lambda level: level.call_oi).strike_price
            if resistance_levels
            else None
        )

        return OptionChainAnalysis(
            symbol=snapshot.symbol,
            observed_at=snapshot.observed_at,
            pcr=round(total_put_oi / total_call_oi, 2) if total_call_oi else 0,
            max_call_oi_strike=max_call.strike_price,
            max_put_oi_strike=max_put.strike_price,
            resistance=resistance,
            support=support,
            levels=levels,
        )

    def security_archives(
        self,
        symbol: str,
        from_date: date,
        to_date: date,
        series: str = "ALL",
    ) -> list[SecurityArchiveRecord]:
        snapshot = self.snapshot_for(symbol)
        records: list[SecurityArchiveRecord] = []
        selected_series = ["EQ"] if series.upper() == "ALL" else [series.upper()]
        for candle in snapshot.candles:
            trade_date = candle.observed_at.date()
            if not from_date <= trade_date <= to_date:
                continue
            for series_value in selected_series:
                delivery_percent = round(35 + self._rng(f"{symbol}{trade_date}").random() * 30, 2)
                deliverable_quantity = int(candle.volume * delivery_percent / 100)
                records.append(
                    SecurityArchiveRecord(
                        symbol=symbol.upper(),
                        series=series_value,
                        trade_date=trade_date,
                        previous_close=candle.previous_close,
                        open_price=candle.open,
                        high_price=candle.high,
                        low_price=candle.low,
                        last_price=candle.close,
                        close_price=candle.close,
                        vwap=round((candle.high + candle.low + candle.close) / 3, 2),
                        total_traded_quantity=candle.volume,
                        turnover=round(candle.volume * candle.close, 2),
                        number_of_trades=max(1, int(candle.volume / 650)),
                        deliverable_quantity=deliverable_quantity,
                        delivery_to_traded_percent=delivery_percent,
                        source="demo_security_archives",
                    )
                )
        return records

    def _rng(self, symbol: str) -> Random:
        return Random(sum(ord(char) for char in symbol.upper()))

    def _trend_for(self, symbol: str) -> float:
        if symbol.upper() in {"CDSL", "BEL", "MCX"}:
            return 0.16
        if symbol.upper() == "ADANIPOWER":
            return -0.03
        return ((abs(hash(symbol)) % 15) - 5) / 100

    def _strike_step(self, price: float) -> int:
        if price < 250:
            return 5
        if price < 1000:
            return 10
        if price < 2500:
            return 20
        return 50
