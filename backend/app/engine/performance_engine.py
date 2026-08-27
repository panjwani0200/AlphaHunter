from app.domain.contracts import PerformanceMetrics

def calculate_performance() -> PerformanceMetrics:
    """
    Simulate historical performance metrics from completed trades.
    In production, this queries the TradingRepository for closed trades.
    """
    
    # Static mock metrics reflecting an institutional-grade strategy
    win_rate = 64.5
    avg_winner = 4200.0
    avg_loser = 1800.0
    
    avg_rr = avg_winner / avg_loser
    expectancy = (win_rate / 100 * avg_winner) - ((1 - win_rate / 100) * avg_loser)
    
    profit_factor = (win_rate * avg_winner) / ((100 - win_rate) * avg_loser)
    
    max_drawdown = 8.4  # percentage
    sharpe_ratio = 2.15
    sortino_ratio = 3.42
    
    return PerformanceMetrics(
        win_rate=round(win_rate, 2),
        avg_rr=round(avg_rr, 2),
        expectancy=round(expectancy, 2),
        max_drawdown=max_drawdown,
        profit_factor=round(profit_factor, 2),
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio
    )
