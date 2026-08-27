from app.domain.contracts import MarketSnapshot, SectorScore

def analyze_sectors(snapshots: list[MarketSnapshot]) -> list[SectorScore]:
    """
    Computes a 0-100 score for each sector based on constituents' performance.
    """
    sector_metrics = {}
    
    for snap in snapshots:
        sect = snap.sector
        if sect in ("Index", "Unknown"):
            continue
            
        if sect not in sector_metrics:
            sector_metrics[sect] = {"change_sum": 0.0, "vol_ratio_sum": 0.0, "count": 0}
            
        sector_metrics[sect]["change_sum"] += snap.change_percent
        vol_ratio = snap.volume / max(1, snap.average_volume_20d)
        sector_metrics[sect]["vol_ratio_sum"] += vol_ratio
        sector_metrics[sect]["count"] += 1
        
    results = []
    for sect, metrics in sector_metrics.items():
        if metrics["count"] == 0:
            results.append(SectorScore(sector=sect, score=50))
            continue
            
        avg_change = metrics["change_sum"] / metrics["count"]
        avg_vol_ratio = metrics["vol_ratio_sum"] / metrics["count"]
        
        # Base 50, adjust by avg change (capped) and volume expansion
        score = 50 + (avg_change * 10) + ((avg_vol_ratio - 1) * 10)
        score = max(0, min(100, int(score)))
        
        results.append(SectorScore(sector=sect, score=score))
        
    # Sort by strongest
    return sorted(results, key=lambda x: x.score, reverse=True)
