from __future__ import annotations

from math import sqrt
from statistics import mean, pstdev

from app.core.config import settings
from app.domain.contracts import BacktestMetrics, MarketCandle


def _compute_streaks(returns: list[float]) -> tuple[int, int]:
    """Return (max_consecutive_wins, max_consecutive_losses)."""
    max_wins = max_losses = current_wins = current_losses = 0
    for ret in returns:
        if ret > 0:
            current_wins += 1
            current_losses = 0
            max_wins = max(max_wins, current_wins)
        else:
            current_losses += 1
            current_wins = 0
            max_losses = max(max_losses, current_losses)
    return max_wins, max_losses


def run_breakout_backtest(candles_by_symbol: dict[str, list[MarketCandle]]) -> BacktestMetrics:
    """
    Breakout replay backtest with:
    - ATR-based position sizing on a fixed capital pool
    - Slippage on entry and exit (configurable)
    - Flat brokerage per leg (configurable)
    - Stop-loss at entry − 1.5×ATR
    - Profit target at entry + 2×ATR (2:1 R:R)
    - Lookahead of up to 10 bars to hit SL or TP before expiry
    """
    capital = settings.backtest_capital
    slippage_pct = settings.backtest_slippage_percent / 100.0
    brokerage_per_leg = settings.backtest_brokerage_per_leg

    returns: list[float] = []
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    equity_curve = [capital]

    for candles in candles_by_symbol.values():
        if len(candles) < 30:
            continue

        for index in range(20, len(candles) - 10):
            window = candles[index - 20 : index]
            resistance = max(candle.high for candle in window)
            average_volume = mean(candle.volume for candle in window)

            # ATR over the window
            true_ranges = [
                max(
                    c.high - c.low,
                    abs(c.high - p.close),
                    abs(c.low - p.close),
                )
                for p, c in zip(window, window[1:], strict=False)
            ]
            atr = mean(true_ranges[-14:]) if len(true_ranges) >= 14 else mean(true_ranges)

            current = candles[index]
            is_signal = current.close > resistance and current.volume > average_volume * 1.4

            # Check if a good outcome happened in next 5 bars (for recall/precision)
            forward_5 = candles[index + 5]
            forward_return_raw = ((forward_5.close - current.close) / current.close) * 100
            is_good_outcome = forward_return_raw > 2.0

            if is_signal:
                # Apply entry slippage
                entry_price = current.close * (1 + slippage_pct)
                stop_loss = entry_price - 1.5 * atr
                target = entry_price + 2.0 * atr

                # Position sizing: risk 2% of current equity per trade
                current_equity = equity_curve[-1]
                risk_amount = current_equity * 0.02
                quantity = max(1, int(risk_amount / (1.5 * atr))) if atr > 0 else 1

                # Simulate bar-by-bar over next 10 bars
                exit_price = None
                for future_candle in candles[index + 1 : index + 11]:
                    if future_candle.low <= stop_loss:
                        exit_price = stop_loss * (1 - slippage_pct)
                        break
                    if future_candle.high >= target:
                        exit_price = target * (1 - slippage_pct)
                        break
                if exit_price is None:
                    # Time-based exit at bar 10 with slippage
                    exit_price = candles[index + 10].close * (1 - slippage_pct)

                # Calculate P&L
                gross_pnl = (exit_price - entry_price) * quantity
                net_pnl = gross_pnl - 2 * brokerage_per_leg  # entry + exit legs
                pnl_pct = (net_pnl / (entry_price * quantity)) * 100

                returns.append(pnl_pct)
                new_equity = equity_curve[-1] + net_pnl
                equity_curve.append(max(0.01, new_equity))

                if pnl_pct > 0:
                    true_positives += 1
                else:
                    false_positives += 1
            elif is_good_outcome:
                false_negatives += 1

    trades = len(returns)
    wins = sum(1 for value in returns if value > 0)
    precision_denominator = true_positives + false_positives
    recall_denominator = true_positives + false_negatives
    false_positive_denominator = false_positives + true_positives

    sharpe = 0.0
    if len(returns) > 1 and pstdev(returns) > 0:
        sharpe = (mean(returns) / pstdev(returns)) * sqrt(252 / 5)

    peak = equity_curve[0]
    max_drawdown = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        max_drawdown = min(max_drawdown, (value - peak) / peak * 100)

    total_return = ((equity_curve[-1] - capital) / capital) * 100 if len(equity_curve) > 1 else 0.0

    avg_return = round(mean(returns), 2) if returns else 0.0
    best_trade = round(max(returns), 2) if returns else 0.0
    worst_trade = round(min(returns), 2) if returns else 0.0
    consec_wins, consec_losses = _compute_streaks(returns)

    return BacktestMetrics(
        trades=trades,
        win_rate=round((wins / trades) * 100, 2) if trades else 0.0,
        precision=round((true_positives / precision_denominator) * 100, 2)
        if precision_denominator
        else 0.0,
        recall=round((true_positives / recall_denominator) * 100, 2) if recall_denominator else 0.0,
        false_positive_rate=round((false_positives / false_positive_denominator) * 100, 2)
        if false_positive_denominator
        else 0.0,
        sharpe_ratio=round(sharpe, 2),
        max_drawdown=round(abs(max_drawdown), 2),
        total_return_percent=round(total_return, 2),
        avg_return_per_trade=avg_return,
        best_trade=best_trade,
        worst_trade=worst_trade,
        consecutive_wins=consec_wins,
        consecutive_losses=consec_losses,
        slippage_applied_percent=settings.backtest_slippage_percent,
        brokerage_per_leg=brokerage_per_leg,
    )
