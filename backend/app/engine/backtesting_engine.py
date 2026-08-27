import numpy as np
import pandas as pd
from typing import Any
from math import sqrt
from statistics import mean, pstdev

class BacktestingEngine:
    def __init__(self) -> None:
        pass

    def run_backtest(self, symbol: str, candles: list[Any], strategy_rules: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Run a backtest on historical daily candles using strategy rules:
        - Default strategy: AlphaHunter v2 (RSI > 55, Volume > 1.5x, Close > 20 SMA)
        - Calculates Sharpe, Sortino, CAGR, Max Drawdown, Profit Factor, Expectancy.
        """
        if len(candles) < 30:
            return {
                "total_trades": 0, "win_rate": 0.0, "sharpe_ratio": 0.0, "sortino_ratio": 0.0,
                "cagr": 0.0, "max_drawdown": 0.0, "profit_factor": 0.0, "expectancy": 0.0,
                "equity_curve": [100000.0], "trades": []
            }

        # Parse rules
        rules = strategy_rules or {
            "rsi_min": 55.0,
            "volume_mult": 1.5,
            "trend_ma": 20
        }

        df = pd.DataFrame([c.model_dump() for c in candles])
        df["ma"] = df["close"].rolling(rules.get("trend_ma", 20)).mean().fillna(df["close"])
        
        # Simple RSI calculation
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14, min_periods=1).mean()
        avg_loss = loss.rolling(window=14, min_periods=1).mean()
        rs = avg_gain / (avg_loss + 0.001)
        df["rsi"] = 100 - (100 / (1 + rs))
        
        # Volatility ATR
        df["tr"] = np.maximum(
            df["high"] - df["low"],
            np.maximum(
                abs(df["high"] - df["close"].shift(1)),
                abs(df["low"] - df["close"].shift(1))
            )
        ).fillna(0.0)
        df["atr"] = df["tr"].rolling(14, min_periods=1).mean()

        capital = 100000.0
        equity = capital
        equity_curve = [capital]
        trades = []
        returns = []

        i = 20
        while i < len(df) - 10:
            row = df.iloc[i]
            
            # Strategy buy condition
            rsi_cond = row["rsi"] > rules.get("rsi_min", 55.0)
            vol_avg = df["volume"].iloc[i-20:i].mean()
            vol_cond = row["volume"] > vol_avg * rules.get("volume_mult", 1.5)
            trend_cond = row["close"] > row["ma"]

            if rsi_cond and vol_cond and trend_cond:
                entry_price = float(row["close"])
                atr_val = float(row["atr"]) if row["atr"] > 0 else (entry_price * 0.015)
                
                sl = entry_price - 1.5 * atr_val
                tp = entry_price + 2.0 * atr_val
                
                # Position sizing (risk 2% of capital per trade)
                risk_amt = equity * 0.02
                qty = int(risk_amt / (entry_price - sl)) if (entry_price - sl) > 0 else 100
                qty = max(1, qty)

                # Slide forward to exit
                exit_price = None
                exit_reason = "TIME_EXIT"
                for j in range(i + 1, min(i + 11, len(df))):
                    future_row = df.iloc[j]
                    if future_row["low"] <= sl:
                        exit_price = sl
                        exit_reason = "STOP_LOSS"
                        i = j
                        break
                    if future_row["high"] >= tp:
                        exit_price = tp
                        exit_reason = "TAKE_PROFIT"
                        i = j
                        break
                
                if exit_price is None:
                    exit_price = float(df["close"].iloc[min(i + 10, len(df)-1)])
                    exit_reason = "TIME_EXIT"
                    i = min(i + 10, len(df)-1)

                gross_pnl = (exit_price - entry_price) * qty
                net_pnl = gross_pnl - 40.0 # flat brokerage
                ret_pct = (net_pnl / (entry_price * qty)) * 100.0
                
                equity += net_pnl
                equity_curve.append(max(1.0, equity))
                returns.append(ret_pct / 100.0)

                trades.append({
                    "entry_date": df.index[i - 10], # approximate timestamp/index
                    "entry_price": round(entry_price, 2),
                    "exit_price": round(exit_price, 2),
                    "pnl": round(net_pnl, 2),
                    "return_pct": round(ret_pct, 2),
                    "reason": exit_reason
                })
            i += 1

        # Summary calculations
        total_trades = len(trades)
        wins = [t for t in trades if t["pnl"] > 0]
        win_rate = round((len(wins) / total_trades) * 100.0, 2) if total_trades > 0 else 0.0

        # Sharpe & Sortino
        sharpe = 0.0
        sortino = 0.0
        if total_trades > 1:
            avg_ret = mean(returns)
            std_ret = pstdev(returns)
            if std_ret > 0:
                sharpe = round((avg_ret / std_ret) * sqrt(252), 2)
                
            neg_returns = [r for r in returns if r < 0]
            neg_std = pstdev(neg_returns) if len(neg_returns) > 1 else 0.0
            if neg_std > 0:
                sortino = round((avg_ret / neg_std) * sqrt(252), 2)

        # CAGR (Compound Annual Growth Rate)
        years = len(df) / 252.0
        cagr = round((((equity / capital) ** (1.0 / years)) - 1.0) * 100.0, 2) if years > 0 and equity > 0 else 0.0

        # Drawdown
        peak = capital
        max_dd = 0.0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100.0
            if dd > max_dd:
                max_dd = dd

        # Profit Factor
        gross_profits = sum(t["pnl"] for t in trades if t["pnl"] > 0)
        gross_losses = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))
        profit_factor = round(gross_profits / (gross_losses or 1.0), 2)

        # Expectancy
        expectancy = round(mean([t["pnl"] for t in trades]), 2) if trades else 0.0

        return {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "cagr": cagr,
            "max_drawdown": round(max_dd, 2),
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "equity_curve": [round(e, 2) for e in equity_curve],
            "trades": trades
        }

# Global Instance
backtesting_engine = BacktestingEngine()
