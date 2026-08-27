from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from app.domain.contracts import ScannerCandidate, SelectedCandidate, SignalType
from app.collectors.market_data.demo import SECTORS
from app.core.config import settings

logger = logging.getLogger(__name__)

class SelectionEngine:
    def __init__(self, top_n: int = 6, min_rr: float = 1.5, max_per_sector: int = 2) -> None:
        self.top_n = top_n
        self.min_rr = min_rr
        self.max_per_sector = max_per_sector
        
        # State management for daily deduplication
        # dict[symbol] -> dict of last alert info (date, signal_type, etc.)
        self._daily_alert_state: dict[str, dict] = {}

    def _get_direction(self, signal: SignalType) -> str:
        value = signal.value.lower()
        if "short" in value:
            return "SHORT"
        return "LONG"
        
    def _is_new_or_material_change(self, symbol: str, signal_type: str, now: datetime) -> bool:
        """
        Check if the symbol was already alerted today for the SAME signal type.
        If it was, return False (to suppress duplicate).
        """
        state = self._daily_alert_state.get(symbol)
        if not state:
            return True
            
        last_date = state.get("date")
        if not last_date or last_date.date() != now.date():
            return True # New day
            
        last_signal = state.get("signal_type")
        if last_signal != signal_type:
            return True # Signal changed (e.g., LONG -> REVERSAL -> SHORT)
            
        return False

    def select_top_opportunities(self, candidates: list[ScannerCandidate]) -> list[SelectedCandidate]:
        """
        Converts the raw ScannerCandidate pool into a heavily filtered and ranked Top-N shortlist.
        """
        now = datetime.now(timezone.utc)
        ist = timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(ist)
        
        # 1. Clear state if a new day started
        if self._daily_alert_state:
            sample_state = next(iter(self._daily_alert_state.values()))
            if sample_state.get("date") and sample_state["date"].date() != now_ist.date():
                logger.info("New trading day detected. Clearing daily alert state.")
                self._daily_alert_state.clear()
        
        eligible_candidates: list[SelectedCandidate] = []
        
        for cand in candidates:
            # 2. Extract RR and Execution Zones
            zones = cand.evidence.get("execution_zones", {})
            rr = zones.get("risk_reward", 0.0)
            
            # Hard RR Filter
            if rr < self.min_rr:
                logger.debug(f"Rejected {cand.symbol}: RR {rr} < {self.min_rr}")
                continue
                
            entry = zones.get("entry", 0.0)
            sl = zones.get("sl", 0.0)
            target = zones.get("target1", 0.0)
            
            if entry <= 0 or sl <= 0 or target <= 0:
                logger.debug(f"Rejected {cand.symbol}: Invalid execution zones {zones}")
                continue
                
            # 3. Deduplication Filter
            if not self._is_new_or_material_change(cand.symbol, cand.signal_type.value, now_ist):
                logger.debug(f"Rejected {cand.symbol}: Already alerted today for {cand.signal_type.value}")
                continue
                
            # 4. Compute Secondary Selection Score
            # Alpha Score (0-100) is the base quality metric. We add tie-breakers.
            # E.g. Alpha (30%) + Trend (15%) + OI (15%) + RR (10%) + Sector (10%) + Volume (10%) + ML (10%)
            # We scale RR up to a max of 10 for score (e.g. RR 3.0 -> 30, capped at 50)
            rr_score = min(rr * 10, 50.0)
            
            selection_score = (
                (cand.score * 0.30) +
                (cand.trend_score * 0.15) +
                (cand.oi_score * 0.15) +
                (rr_score * 0.10) +
                (cand.sector_strength_score * 0.10) +
                (cand.volume_score * 0.10) +
                (cand.ml_score * 0.10)
            )
            
            direction = self._get_direction(cand.signal_type)
            
            reasons = cand.reasons[:3] if cand.reasons else ["Excellent setup conditions"]
            
            eligible_candidates.append(
                SelectedCandidate(
                    symbol=cand.symbol,
                    signal_type=cand.signal_type,
                    direction=direction,
                    alpha_score=round(cand.score, 2),
                    selection_score=round(selection_score, 2),
                    entry=entry,
                    sl=sl,
                    target=target,
                    risk_reward=round(rr, 2),
                    setup_notes=reasons
                )
            )
            
        # 5. Rank by Selection Score
        eligible_candidates.sort(key=lambda x: x.selection_score, reverse=True)
        
        # 6. Sector Diversification
        final_selection: list[SelectedCandidate] = []
        sector_counts: dict[str, int] = {}
        
        for cand in eligible_candidates:
            if len(final_selection) >= self.top_n:
                break
                
            sector = SECTORS.get(cand.symbol, "Unknown")
            count = sector_counts.get(sector, 0)
            
            if count >= self.max_per_sector:
                logger.debug(f"Rejected {cand.symbol}: Max sector concentration reached for {sector}")
                continue
                
            sector_counts[sector] = count + 1
            final_selection.append(cand)
            
        # 7. Update Daily State for the selected candidates
        for cand in final_selection:
            self._daily_alert_state[cand.symbol] = {
                "date": now_ist,
                "signal_type": cand.signal_type.value
            }
            
        logger.info(
            f"Selection Engine: Candidates={len(candidates)}, Eligible={len(eligible_candidates)}, Selected={len(final_selection)}"
        )
            
        return final_selection
