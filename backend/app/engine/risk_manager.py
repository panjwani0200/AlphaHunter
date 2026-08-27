from app.domain.contracts import PortfolioRisk, PositionHealth, MarketSnapshot

def evaluate_portfolio_risk(
    positions: list[PositionHealth],
    snapshots: dict[str, MarketSnapshot]
) -> PortfolioRisk:
    
    if not positions:
        return PortfolioRisk(
            portfolio_risk="LOW",
            suggested_allocation={}
        )
        
    sector_exposure = {}
    suggested_alloc = {}
    
    total_positions = len(positions)
    base_weight = 1.0 / total_positions
    
    # 1. Sector Concentration
    for pos in positions:
        snap = snapshots.get(pos.symbol)
        if snap:
            sect = snap.sector
            sector_exposure[sect] = sector_exposure.get(sect, 0) + base_weight
            
    max_exposure = max(sector_exposure.values()) if sector_exposure else 0.0
    
    if max_exposure > 0.4:
        risk = "HIGH"
    elif max_exposure > 0.25:
        risk = "MODERATE"
    else:
        risk = "LOW"
        
    # 2. Suggested Allocation based on Health Score
    total_health = sum(pos.health_score for pos in positions)
    
    if total_health == 0:
        suggested_alloc = {pos.symbol: base_weight for pos in positions}
    else:
        for pos in positions:
            # Overweight high conviction
            weight = pos.health_score / total_health
            suggested_alloc[pos.symbol] = round(weight, 2)
            
    return PortfolioRisk(
        portfolio_risk=risk,
        suggested_allocation=suggested_alloc
    )
