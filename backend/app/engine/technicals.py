from __future__ import annotations

from statistics import mean

from app.domain.contracts import MarketCandle, TechnicalAnalysis, VolumeTrend


def _ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    multiplier = 2 / (period + 1)
    ema_value = mean(values[:period])
    for value in values[period:]:
        ema_value = (value - ema_value) * multiplier + ema_value
    return round(ema_value, 2)


def _rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for previous, current in zip(values, values[1:], strict=False):
        change = current - previous
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))
    average_gain = mean(gains[-period:])
    average_loss = mean(losses[-period:])
    if average_loss == 0:
        return 100.0
    relative_strength = average_gain / average_loss
    return round(100 - (100 / (1 + relative_strength)), 2)


def _atr(candles: list[MarketCandle], period: int = 14) -> float | None:
    if len(candles) <= period:
        return None
    true_ranges: list[float] = []
    for previous, current in zip(candles, candles[1:], strict=False):
        true_ranges.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
    return round(mean(true_ranges[-period:]), 2)


def _macd(values: list[float]) -> tuple[float | None, float | None, float | None]:
    """Returns (macd_line, signal_line, histogram). Requires at least 35 bars."""
    if len(values) < 35:
        return None, None, None
    fast = _ema(values, 12)
    slow = _ema(values, 26)
    if fast is None or slow is None:
        return None, None, None
    # Build full MACD line series for signal calculation
    macd_series: list[float] = []
    for i in range(26, len(values) + 1):
        f = _ema(values[:i], 12)
        s = _ema(values[:i], 26)
        if f is not None and s is not None:
            macd_series.append(f - s)
    if len(macd_series) < 9:
        return None, None, None
    macd_line = macd_series[-1]
    signal_line = _ema(macd_series, 9)
    if signal_line is None:
        return None, None, None
    histogram = macd_line - signal_line
    return round(macd_line, 4), round(signal_line, 4), round(histogram, 4)


def _bollinger_bands(
    values: list[float], period: int = 20, std_dev: float = 2.0
) -> tuple[float | None, float | None, float | None, float | None]:
    """Returns (upper, middle, lower, width_pct). Requires at least `period` values."""
    if len(values) < period:
        return None, None, None, None
    window = values[-period:]
    middle = mean(window)
    variance = sum((x - middle) ** 2 for x in window) / period
    std = variance ** 0.5
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    width_pct = round(((upper - lower) / middle) * 100, 2) if middle else 0.0
    return round(upper, 2), round(middle, 2), round(lower, 2), width_pct


def _adx(candles: list[MarketCandle], period: int = 14) -> float | None:
    """Average Directional Index — trend strength regardless of direction."""
    if len(candles) < period * 2 + 1:
        return None
    plus_dm: list[float] = []
    minus_dm: list[float] = []
    true_ranges: list[float] = []
    for prev, curr in zip(candles, candles[1:], strict=False):
        up_move = curr.high - prev.high
        down_move = prev.low - curr.low
        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)
        true_ranges.append(
            max(curr.high - curr.low, abs(curr.high - prev.close), abs(curr.low - prev.close))
        )
    if len(true_ranges) < period:
        return None
    atr_val = mean(true_ranges[-period:])
    if atr_val == 0:
        return None
    plus_di = 100 * mean(plus_dm[-period:]) / atr_val
    minus_di = 100 * mean(minus_dm[-period:]) / atr_val
    di_sum = plus_di + minus_di
    if di_sum == 0:
        return 0.0
    dx = 100 * abs(plus_di - minus_di) / di_sum
    return round(dx, 2)


def _volume_trend(candles: list[MarketCandle]) -> VolumeTrend:
    if len(candles) < 20:
        return VolumeTrend.FLAT
    avg_recent = mean(candle.volume for candle in candles[-5:])
    avg_baseline = mean(candle.volume for candle in candles[-20:-5])
    if avg_baseline == 0:
        return VolumeTrend.FLAT
    ratio = avg_recent / avg_baseline
    if ratio > 1.15:
        return VolumeTrend.RISING
    if ratio < 0.85:
        return VolumeTrend.FALLING
    return VolumeTrend.FLAT


def analyze_technicals(symbol: str, candles: list[MarketCandle]) -> TechnicalAnalysis:
    if not candles:
        return TechnicalAnalysis(symbol=symbol)

    closes = [candle.close for candle in candles]
    highs = [candle.high for candle in candles]
    lows = [candle.low for candle in candles]
    latest_close = closes[-1]

    ema_20 = _ema(closes, 20)
    ema_50 = _ema(closes, 50)
    ema_100 = _ema(closes, 100)
    ema_200 = _ema(closes, 200)
    rsi_14 = _rsi(closes)
    atr_14 = _atr(candles)
    macd_line, macd_signal, macd_hist = _macd(closes)
    bb_upper, bb_middle, bb_lower, bb_width = _bollinger_bands(closes)
    adx = _adx(candles)
    vol_trend = _volume_trend(candles)

    support = round(min(lows[-20:]), 2)
    resistance = round(max(highs[-20:]), 2)

    week52_candles = candles[-252:] if len(candles) >= 252 else candles
    week52_high = round(max(c.high for c in week52_candles), 2)
    week52_low = round(min(c.low for c in week52_candles), 2)

    trend = "sideways"
    if ema_20 and ema_50 and latest_close > ema_20 > ema_50:
        trend = "up"
    elif ema_20 and ema_50 and latest_close < ema_20 < ema_50:
        trend = "down"

    breakout_quality = 0.0
    if resistance and latest_close >= resistance * 0.995:
        volume_values = [candle.volume for candle in candles[-20:]]
        average_volume = mean(volume_values[:-1]) if len(volume_values) > 1 else volume_values[-1]
        volume_ratio = candles[-1].volume / average_volume if average_volume else 1
        breakout_quality = min(100.0, 50 + (volume_ratio - 1) * 25)

    return TechnicalAnalysis(
        symbol=symbol,
        ema_20=ema_20,
        ema_50=ema_50,
        ema_100=ema_100,
        ema_200=ema_200,
        rsi_14=rsi_14,
        macd=macd_line,
        macd_signal=macd_signal,
        macd_histogram=macd_hist,
        adx=adx,
        atr_14=atr_14,
        bb_upper=bb_upper,
        bb_lower=bb_lower,
        bb_middle=bb_middle,
        bb_width=bb_width,
        support=support,
        resistance=resistance,
        week52_high=week52_high,
        week52_low=week52_low,
        trend=trend,
        volume_trend=vol_trend,
        breakout_quality=round(max(0.0, breakout_quality), 2),
    )
