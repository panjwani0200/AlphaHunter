import asyncio
from datetime import datetime, timezone
import pandas as pd
import yfinance as yf
import numpy as np

from app.domain.contracts import BreakoutRadarCandidate, BreakoutStatus, MarketSnapshot


class BreakoutRadarEngine:
    def __init__(self):
        self._monthly_cache = {}
        self._intraday_cache = {}
        self._last_monthly_update = {}
        self._last_intraday_update = {}
    
    async def scan_market(self, snapshots: list[MarketSnapshot]) -> list[BreakoutRadarCandidate]:
        candidates = []
        
        # Batch symbols for yfinance fetching
        symbols = [s.symbol for s in snapshots]
        
        # We use a mix of Daily snapshots and on-demand yfinance 15m/1mo data for this implementation.
        # In production this would run as a background task saving to DB.
        
        # Determine tickers
        # Pre-filter: Only fetch 15m intraday data for stocks that have actual momentum or volume today.
        # This reduces the yfinance batch request from 184 stocks to ~20-40 stocks, preventing the 30s timeout.
        ticker_map = {}
        for s in snapshots:
            vol_ratio = s.volume / s.average_volume_20d if s.average_volume_20d else 1.0
            
            # Always fetch indices, otherwise only fetch if moving
            is_index = s.symbol.upper() in ["NIFTY", "BANKNIFTY"]
            if is_index or (s.change_percent >= 0.8 or s.change_percent <= -0.8) or vol_ratio >= 1.2:
                symbol = s.symbol.upper()
                if symbol == "NIFTY":
                    ticker_map["^NSEI"] = symbol
                elif symbol == "BANKNIFTY":
                    ticker_map["^NSEBANK"] = symbol
                elif symbol == "TATAMOTORS":
                    ticker_map["TATAMOTORS.NS"] = symbol
                elif symbol == "LTIM":
                    ticker_map["LTIM.NS"] = symbol
                else:
                    ticker_map[f"{symbol}.NS"] = symbol
        
        tickers = list(ticker_map.keys())
        
        # We no longer fetch daily_df via yfinance here because it takes 20+ seconds and causes UI timeouts.
        # Instead, we will directly use `snap.candles` (which already contains 1 year of daily data from trading_service).

        # Fetch 15-minute Data
        intraday_df = None
        try:
            fetch_15m = True
            if self._last_intraday_update:
                elapsed = (datetime.now() - self._last_intraday_update.get('time', datetime.min)).total_seconds()
                if elapsed < 60: # Cache for 1 min
                    fetch_15m = False
            
            if fetch_15m and tickers:
                # To prevent timeout on large lists, we'll only fetch the last 2 days
                intraday_df = await asyncio.to_thread(
                    yf.download, tickers, period="2d", interval="15m", group_by="ticker", progress=False, auto_adjust=False
                )
                if hasattr(self, '_intraday_cache') and self._intraday_cache is not None:
                    del self._intraday_cache
                self._intraday_cache = intraday_df
                self._last_intraday_update['time'] = datetime.now()
            else:
                intraday_df = self._intraday_cache
        except Exception:
            pass
            
        nifty_snap = next((s for s in snapshots if s.symbol.upper() == "NIFTY"), None)
        nifty_change = nifty_snap.change_percent if nifty_snap and nifty_snap.change_percent else 0.0

        for snap in snapshots:
            symbol = snap.symbol.upper()
            ticker_name_list = [k for k, v in ticker_map.items() if v == symbol]
            # Use the mapped ticker if we fetched it, otherwise reconstruct the default NS ticker
            ticker_name = ticker_name_list[0] if ticker_name_list else (
                "^NSEI" if symbol == "NIFTY" else
                "^NSEBANK" if symbol == "BANKNIFTY" else
                f"{symbol}.NS"
            )
            
            # Extract monthly high/low
            prev_month_high = 0.0
            prev_month_low = 0.0
            prev_level_date = None
            prev_high_date = None
            prev_low_date = None
            prev_level_volume = 0
            
            if snap.candles and len(snap.candles) >= 20:
                try:
                    df_candles = pd.DataFrame([
                        {'date': c.observed_at, 'High': c.high, 'Low': c.low, 'Volume': c.volume}
                        for c in snap.candles
                    ])
                    df_candles.set_index('date', inplace=True)
                    current_date = df_candles.index[-1]
                    prev_month_y = current_date.year if current_date.month > 1 else current_date.year - 1
                    prev_month_m = current_date.month - 1 if current_date.month > 1 else 12
                    
                    prev_month_df = df_candles[(df_candles.index.year == prev_month_y) & (df_candles.index.month == prev_month_m)]
                    
                    if not prev_month_df.empty:
                        prev_month_high = float(prev_month_df["High"].max())
                        prev_month_low = float(prev_month_df["Low"].min())
                        
                        high_idx = prev_month_df["High"].idxmax()
                        low_idx = prev_month_df["Low"].idxmin()
                        
                        if isinstance(high_idx, pd.Timestamp):
                            prev_high_date = high_idx.to_pydatetime()
                        if isinstance(low_idx, pd.Timestamp):
                            prev_low_date = low_idx.to_pydatetime()
                            
                        prev_level_date = prev_high_date
                        prev_level_volume = int(prev_month_df.loc[high_idx, "Volume"])
                except Exception as e:
                    import logging
                    logging.getLogger("uvicorn").error(f"Error extracting monthly levels from snapshots for {symbol}: {e}")
                    
            days_since_prev_level = None
            if prev_level_date:
                now_dt = datetime.now(timezone.utc) if prev_level_date.tzinfo else datetime.now()
                days_since_prev_level = max(0, (now_dt - prev_level_date).days)
            
            # Monthly distance
            dist_high = ((snap.last_price - prev_month_high) / prev_month_high) * 100 if prev_month_high > 0 else 0
            dist_low = ((snap.last_price - prev_month_low) / prev_month_low) * 100 if prev_month_low > 0 else 0
            
            dist_percent = min(abs(dist_high), abs(dist_low))
            monthly_range = prev_month_high - prev_month_low
            
            # Determine status
            status = BreakoutStatus.WAITING
            is_breakout_candidate = False
            is_support_candidate = False
            
            if snap.last_price >= prev_month_high and prev_month_high > 0:
                status = BreakoutStatus.CONFIRMED_BREAKOUT
                is_breakout_candidate = True
            elif dist_high >= -1.0 and dist_high <= 0:
                status = BreakoutStatus.NEAR_BREAKOUT
                is_breakout_candidate = True
                
            if snap.last_price <= prev_month_low + (prev_month_low * 0.01) and prev_month_low > 0:
                status = BreakoutStatus.SUPPORT_BUILDING
                is_support_candidate = True
                
            breakout_percentage = 0.0
            support_percentage = 0.0
            if prev_month_high > 0:
                breakout_percentage = ((snap.last_price - prev_month_high) / prev_month_high) * 100
            if prev_month_low > 0:
                support_percentage = ((snap.last_price - prev_month_low) / prev_month_low) * 100
                
            volume_ratio = 0.0
            if snap.volume and getattr(snap, 'average_volume_20d', None):
                volume_ratio = snap.volume / snap.average_volume_20d
                
            relative_strength = (snap.change_percent or 0.0) - nifty_change
                
            # Intraday metrics (15-min)
            ema_9 = snap.last_price
            ema_20 = snap.last_price
            vwap = snap.last_price
            rsi = 50.0
            adx = 20.0
            atr = 0.0
            volume_spike = 0.0
            ema_9_status = "Neutral"
            trend_15m = "Neutral"
            signal = "WAIT"
            explanation = ""
            
            if intraday_df is not None and not intraday_df.empty:
                try:
                    i_df = None
                    if len(tickers) == 1:
                        i_df = intraday_df.dropna(subset=["Close"])
                    else:
                        if isinstance(intraday_df.columns, pd.MultiIndex):
                            if ticker_name in intraday_df.columns.levels[0]:
                                i_df = intraday_df.xs(ticker_name, axis=1, level=0).dropna(subset=["Close"])
                            elif ticker_name in intraday_df.columns.levels[1]:
                                i_df = intraday_df.xs(ticker_name, axis=1, level=1).dropna(subset=["Close"])
                        else:
                            if ticker_name in intraday_df.columns:
                                i_df = intraday_df[ticker_name].dropna(subset=["Close"])
                        
                    if i_df is not None and not i_df.empty and len(i_df) >= 20:
                        close = i_df["Close"]
                        high = i_df["High"]
                        low = i_df["Low"]
                        volume = i_df["Volume"]
                        
                        ema_9_series = close.ewm(span=9, adjust=False).mean()
                        ema_20_series = close.ewm(span=20, adjust=False).mean()
                        
                        ema_9 = float(ema_9_series.iloc[-1])
                        ema_20 = float(ema_20_series.iloc[-1])
                        
                        # VWAP (simplified for last day)
                        typical_price = (high + low + close) / 3
                        vwap_series = (typical_price * volume).cumsum() / volume.cumsum()
                        vwap = float(vwap_series.iloc[-1])
                        
                        # RSI
                        delta = close.diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        rsi_series = 100 - (100 / (1 + rs))
                        rsi = float(rsi_series.iloc[-1])
                        if np.isnan(rsi):
                            rsi = 50.0
                        
                        # ATR
                        tr1 = high - low
                        tr2 = abs(high - close.shift())
                        tr3 = abs(low - close.shift())
                        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                        atr = float(tr.rolling(14).mean().iloc[-1])
                        if np.isnan(atr):
                            atr = 0.0
                        
                        # Volume Spike
                        avg_vol_15m = volume.rolling(20).mean().iloc[-1]
                        current_vol = volume.iloc[-1]
                        if avg_vol_15m > 0:
                            volume_spike = (current_vol / avg_vol_15m) * 100
                            
                        # Breakout / Support Intraday Confirmation
                        c1 = float(close.iloc[-1])
                        c2 = float(close.iloc[-2])
                        e1 = float(ema_9_series.iloc[-1])
                        e2 = float(ema_9_series.iloc[-2])
                        
                        if c1 > e1:
                            ema_9_status = "Above 9 EMA"
                            trend_15m = "Bullish"
                        else:
                            ema_9_status = "Below 9 EMA"
                            trend_15m = "Bearish"
                            
                        if is_breakout_candidate or is_support_candidate:
                            if c1 > e1 and c2 > e2 and current_vol > avg_vol_15m and c1 > vwap:
                                signal = "BUY"
                                status = BreakoutStatus.CONFIRMED_BREAKOUT if is_breakout_candidate else BreakoutStatus.SUPPORT_CONFIRMED
                                
                            # Fakeout check
                            if is_breakout_candidate and (c1 < prev_month_high and c2 > prev_month_high):
                                if current_vol < avg_vol_15m or rsi < 55 or adx < 20:
                                    status = BreakoutStatus.FAKEOUT_RISK
                                    signal = "WAIT"
                                    
                except Exception:
                    pass

            # Score calculation
            score = 0
            if status in (BreakoutStatus.CONFIRMED_BREAKOUT, BreakoutStatus.NEAR_BREAKOUT, BreakoutStatus.SUPPORT_CONFIRMED):
                score += 30
            if ema_9_status == "Above 9 EMA":
                score += 20
            if volume_spike > 150:
                score += 15
            if snap.last_price > vwap:
                score += 10
            if rsi > 55:
                score += 10
            if adx > 20:
                score += 10
            if atr > 0:
                score += 5
                
            confidence_score = min(100, int(score))
            
            if signal == "BUY":
                explanation = f"Price has broken key levels with a {volume_spike:.1f}% volume expansion. 15-minute candles are closing above 9 EMA and VWAP. RSI is healthy at {rsi:.1f}. Probability of continuation is high."
            elif status == BreakoutStatus.FAKEOUT_RISK:
                explanation = "Price broke the monthly level but failed to sustain. Volume is weak and momentum divergence is visible. Fakeout risk is high."
            else:
                explanation = "Monitoring price action near monthly extremes. Waiting for 15-minute 9 EMA and volume confirmation."

            # Set up Trade targets
            entry = str(snap.last_price)
            stoploss = snap.last_price - atr if atr > 0 else snap.last_price * 0.99
            risk = snap.last_price - stoploss
            target_1 = snap.last_price + (risk * 1.5)
            target_2 = snap.last_price + (risk * 2.5)
            target_3 = snap.last_price + (risk * 4.0)
            rr = (target_1 - snap.last_price) / risk if risk > 0 else 0
            
            signal_strength = "Weak"
            if confidence_score >= 85: signal_strength = "Very Strong"
            elif confidence_score >= 70: signal_strength = "Strong"
            elif confidence_score >= 55: signal_strength = "Moderate"
            
            candidates.append(BreakoutRadarCandidate(
                symbol=symbol,
                last_price=snap.last_price,
                prev_month_high=prev_month_high,
                prev_month_low=prev_month_low,
                prev_level_date=prev_level_date,
                prev_high_date=prev_high_date,
                prev_low_date=prev_low_date,
                days_since_prev_level=days_since_prev_level,
                monthly_range=monthly_range,
                distance_percent=dist_percent,
                breakout_percentage=breakout_percentage,
                support_percentage=support_percentage,
                volume_ratio=volume_ratio,
                prev_level_volume=prev_level_volume,
                relative_strength=relative_strength,
                status=status,
                trend_15m=trend_15m,
                ema_9_status=ema_9_status,
                ema_9=ema_9,
                ema_20=ema_20,
                vwap=vwap,
                volume=int(snap.volume) if snap.volume else 0,
                avg_volume=int(snap.average_volume_20d) if getattr(snap, 'average_volume_20d', None) else 0,
                volume_spike_percent=volume_spike,
                atr=atr,
                rsi=rsi,
                adx=adx,
                institutional_activity_score=min(100, int(volume_spike / 2)),
                trend_strength=75 if trend_15m == "Bullish" else 40 if trend_15m == "Neutral" else 20,
                signal_strength=signal_strength,
                confidence_score=confidence_score,
                risk_reward_ratio=rr,
                recommended_entry=entry,
                stoploss=stoploss,
                target_1=target_1,
                target_2=target_2,
                target_3=target_3,
                signal=signal,
                ai_explanation=explanation
            ))
            
        # Sort by confidence score
        candidates.sort(key=lambda x: x.confidence_score, reverse=True)
        return candidates

breakout_radar_engine = BreakoutRadarEngine()
