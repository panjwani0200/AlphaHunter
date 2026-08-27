from app.domain.contracts import MarketCandle, FibResult

def analyze_fibonacci(candles: list[MarketCandle]) -> FibResult:
    if len(candles) < 60:
        return FibResult(fib_zone="NONE", confluence=False, score=50)

    # Use the last 60 candles to find the swing high and low
    recent_candles = candles[-60:]
    swing_high = max(c.high for c in recent_candles)
    swing_low = min(c.low for c in recent_candles)
    
    if swing_high == swing_low:
        return FibResult(fib_zone="NONE", confluence=False, score=50)

    latest_price = recent_candles[-1].close
    
    # Check if the overall trend is up or down to calculate retracement from the correct side
    high_idx = next(i for i, c in enumerate(recent_candles) if c.high == swing_high)
    low_idx = next(i for i, c in enumerate(recent_candles) if c.low == swing_low)
    
    is_uptrend = low_idx < high_idx
    
    fib_range = swing_high - swing_low
    
    if is_uptrend:
        # Retracement from swing high down to swing low
        fib_0_382 = swing_high - 0.382 * fib_range
        fib_0_5 = swing_high - 0.5 * fib_range
        fib_0_618 = swing_high - 0.618 * fib_range
        fib_0_786 = swing_high - 0.786 * fib_range
        
        # Golden zone is 0.5 to 0.618
        if fib_0_618 <= latest_price <= fib_0_5:
            return FibResult(fib_zone="0.618", confluence=True, score=90)
        elif fib_0_5 < latest_price <= fib_0_382:
            return FibResult(fib_zone="0.382", confluence=False, score=70)
        elif fib_0_786 <= latest_price < fib_0_618:
            return FibResult(fib_zone="0.786", confluence=False, score=60)
            
    else:
        # Retracement from swing low up to swing high
        fib_0_382 = swing_low + 0.382 * fib_range
        fib_0_5 = swing_low + 0.5 * fib_range
        fib_0_618 = swing_low + 0.618 * fib_range
        fib_0_786 = swing_low + 0.786 * fib_range
        
        # Golden zone is 0.5 to 0.618
        if fib_0_5 <= latest_price <= fib_0_618:
            return FibResult(fib_zone="0.618", confluence=True, score=90)
        elif fib_0_382 <= latest_price < fib_0_5:
            return FibResult(fib_zone="0.382", confluence=False, score=70)
        elif fib_0_618 < latest_price <= fib_0_786:
            return FibResult(fib_zone="0.786", confluence=False, score=60)

    return FibResult(fib_zone="NONE", confluence=False, score=50)
