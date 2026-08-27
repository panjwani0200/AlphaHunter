from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import asyncio

from app.ai.analyst import explain_candidate, explain_trade_health, summarize_portfolio
from app.alerts.telegram import TelegramNotifier
from app.collectors.market_data.demo import DEFAULT_SYMBOLS, DemoMarketDataCollector
from app.collectors.market_data.yahoo import YahooMarketDataCollector
from app.collectors.nse.live_quotes import NseLiveQuoteCollector
from app.collectors.nse.options_chain import NseOptionsChainCollector
from app.core.config import settings
from app.services.analysis_export import AnalysisExportService
from app.db.repository import TradingRepository
from app.collectors.nse.security_archives import NseSecurityArchiveCollector
from app.domain.contracts import (
    AlertAction,
    AlertMessage,
    AlertType,
    BacktestMetrics,
    LiveQuote,
    MarketCandle,
    MarketOverview,
    MarketSnapshot,
    OiInterpretation,
    OiSnapshot,
    OptionChainAnalysis,
    OptionChainFull,
    OptionLevel,
    OptionSuggestion,
    PositionInput,
    PositionState,
    ScannerCandidate,
    SecurityArchiveRecord,
)
from app.engine.backtesting import run_breakout_backtest
from app.engine.reversal import assess_reversal
from app.engine.scoring import score_candidate
from app.engine.technicals import analyze_technicals
from app.engine.trade_health import score_trade_health

from app.domain.contracts import (
    MarketRegime, SectorScore, PortfolioRisk, EventRisk,
    OptionGreeks, PerformanceMetrics, ThesisValidationResult, 
    PositionHealth
)
from app.engine.regime_engine import detect_market_regime
from app.engine.sector_engine import analyze_sectors
from app.engine.event_engine import evaluate_event_risk
from app.engine.risk_manager import evaluate_portfolio_risk
from app.engine.performance_engine import calculate_performance
from app.engine.thesis_engine import evaluate_thesis
from app.engine.position_monitor import evaluate_position_health
from app.engine.greeks_engine import calculate_greeks
from app.engine.trade_recommendation import generate_trade_card
from app.engine.exit_engine import evaluate_exit
from app.engine.notification_engine import NotificationEnginePro
from app.domain.contracts import TradeCard, ExitSignal

def _get_yfinance_quotes(symbols: list[str]) -> dict[str, LiveQuote]:
    import yfinance as yf
    import pandas as pd
    from app.collectors.market_data.demo import SECTORS
    
    results = {}
    if not symbols:
        return results
        
    ticker_map = {}
    for s in symbols:
        symbol_upper = s.upper()
        if symbol_upper == "NIFTY":
            ticker_map["^NSEI"] = symbol_upper
        elif symbol_upper == "BANKNIFTY":
            ticker_map["^NSEBANK"] = symbol_upper
        elif symbol_upper == "TATAMOTORS":
            ticker_map["TATAMOTORS.NS"] = symbol_upper
        elif symbol_upper == "LTIM":
            ticker_map["LTIM.NS"] = symbol_upper
        else:
            ticker_map[f"{symbol_upper}.NS"] = symbol_upper
            
    try:
        tickers = list(ticker_map.keys())
        df = yf.download(tickers, period="5d", progress=False, group_by="ticker", auto_adjust=False)
        
        for ticker_name, symbol_upper in ticker_map.items():
            try:
                if len(tickers) == 1:
                    frame = df
                else:
                    frame = df[ticker_name]
                
                frame = frame.dropna(subset=["Close"])
                frame = frame.fillna(0)
                if frame.empty:
                    continue
                    
                latest_row = frame.iloc[-1]
                prev_row = frame.iloc[-2] if len(frame) > 1 else latest_row
                
                close_val = latest_row["Close"]
                if isinstance(close_val, pd.Series):
                    close_val = close_val.iloc[0]
                    
                prev_close = prev_row["Close"]
                if isinstance(prev_close, pd.Series):
                    prev_close = prev_close.iloc[0]
                    
                vol_val = latest_row["Volume"]
                if isinstance(vol_val, pd.Series):
                    vol_val = vol_val.iloc[0]
                
                last_price = float(close_val)
                prev_close = float(prev_close)
                change = last_price - prev_close
                change_percent = (change / prev_close) * 100 if prev_close > 0 else 0.0
                
                sector = "Unknown"
                if symbol_upper not in {"NIFTY", "BANKNIFTY"}:
                    sector = SECTORS.get(symbol_upper, "Unknown")
                    
                results[symbol_upper] = LiveQuote(
                    symbol=symbol_upper,
                    observed_at=datetime.now(timezone.utc),
                    last_price=round(last_price, 2),
                    previous_close=round(prev_close, 2),
                    change=round(change, 2),
                    change_percent=round(change_percent, 2),
                    volume=int(vol_val or 0),
                    sector=sector,
                    source="yfinance_live",
                )
            except Exception:
                pass
    except Exception as e:
        import logging
        logging.getLogger("uvicorn").warning(f"Failed to fetch batch quotes from yfinance: {e}")
        
    return results


class TradingService:
    def __init__(self) -> None:
        self.demo_collector = DemoMarketDataCollector(DEFAULT_SYMBOLS)
        self.collector = self.demo_collector
        self._market_data_provider = "demo"
        if settings.market_data_provider == "yfinance":
            try:
                self.collector = YahooMarketDataCollector()
                self._market_data_provider = "yfinance"
            except RuntimeError:
                self.collector = self.demo_collector
        self.notifier = TelegramNotifier()
        self.security_archive_collector = NseSecurityArchiveCollector()
        self.exporter = AnalysisExportService()
        self.repository = TradingRepository() if settings.database_enabled else None
        
        from app.engine.selection_engine import SelectionEngine
        self.selection_engine = SelectionEngine(top_n=6, min_rr=1.5, max_per_sector=2)

        # 🚨 Live NSE collectors (only instantiated when enabled) 🚨─────────────────
        self._live_quote_collector: NseLiveQuoteCollector | None = (
            NseLiveQuoteCollector(cache_ttl_seconds=settings.nse_cache_ttl_seconds)
            if settings.nse_live_quotes_enabled else None
        )
        self._options_collector: NseOptionsChainCollector | None = (
            NseOptionsChainCollector(cache_ttl_seconds=settings.nse_cache_ttl_seconds)
            if settings.nse_options_chain_enabled else None
        )
        self._latest_snapshots: dict[str, MarketSnapshot] = {}
        self._latest_candidates: list[ScannerCandidate] = []
        self._positions: dict[str, PositionState] = {}
        self._alerts: list[AlertMessage] = []
        self._active_symbols: set[str] = set(DEFAULT_SYMBOLS)
        self._snapshots_lock: asyncio.Lock | None = None
        self._load_positions_from_storage()
        


    @property
    def database_enabled(self) -> bool:
        return self.repository is not None

    @property
    def telegram_enabled(self) -> bool:
        return self.notifier.enabled

    @property
    def market_data_provider(self) -> str:
        return self._market_data_provider

    def database_connected(self) -> bool:
        if not self.repository:
            return False
        return self.repository.database_connected()

    def readiness(self) -> dict[str, object]:
        database_connected = self.database_connected() if self.repository else False
        return {
            "status": "ready" if self._latest_snapshots or self.market_data_provider == "demo" else "warming_up",
            "market_data_provider": self.market_data_provider,
            "database": {
                "enabled": self.database_enabled,
                "connected": database_connected,
                "last_error": self.repository.last_error if self.repository else None,
            },
            "telegram": {"enabled": self.telegram_enabled},
            "scheduler": {"enabled": settings.start_scheduler},
            "runtime": {
                "snapshots_cached": len(self._latest_snapshots),
                "positions_cached": len(self._positions),
                "alerts_cached": len(self._alerts),
            },
        }

    async def _background_update_snapshots(self):
        async with self._snapshots_lock:
            # Offload blocking network calls to a threadpool to prevent freezing the FastAPI event loop
            snapshots = await asyncio.to_thread(self._collect_snapshots)
            
            from app.engine.cycle_engine import detect_cycle_phase
            from app.engine.technicals import analyze_technicals
            
            for snap in snapshots:
                technicals = analyze_technicals(snap.symbol, snap.candles)
                # We skip live options chain fetching for the bulk get_snapshots() method
                # to prevent 180+ sequential network requests which cause the dashboard to timeout.
                # Individual endpoints can fetch options chains on-demand.
                oi_snapshot = self.demo_collector.oi_for(snap)
                    
                snap.cycle_metrics = detect_cycle_phase(snap, technicals, oi_snapshot)
                
                # Track cycle transitions and alert
                if not hasattr(self, "_previous_cycles"):
                    self._previous_cycles = {}
                    
                old_cycle = self._previous_cycles.get(snap.symbol)
                new_cycle = snap.cycle_metrics.phase.value
                
                if old_cycle and old_cycle != new_cycle:
                    from app.engine.notification_engine import NotificationEnginePro
                    rec = "Watch closely"
                    if new_cycle == "accumulation":
                        rec = "Breakout watch recommended"
                    elif new_cycle == "markup":
                        rec = "Bullish continuation likely"
                    elif new_cycle == "distribution":
                        rec = "Profit booking risk rising"
                    elif new_cycle == "markdown":
                        rec = "Bearish continuation likely"
                        
                    NotificationEnginePro.dispatch_cycle_alert(
                        symbol=snap.symbol,
                        phase=new_cycle.upper(),
                        confidence=snap.cycle_metrics.confidence,
                        recommended_action=rec
                    )
                self._previous_cycles[snap.symbol] = new_cycle

            self._latest_snapshots = {s.symbol.upper(): s for s in snapshots}
            self._last_snapshots_time = datetime.now(timezone.utc)
            
            # (Selection engine candidates are updated by the scanner job, not here)

    async def get_snapshots(self) -> list[MarketSnapshot]:
        now = datetime.now(timezone.utc)
        
        # 1. Fast path: If we have a fresh cache, return it instantly
        if hasattr(self, "_last_snapshots_time") and self._latest_snapshots:
            if (now - self._last_snapshots_time).total_seconds() < 10:
                return list(self._latest_snapshots.values())
        
        # Lazy initialization of the asyncio.Lock to bind to the active event loop
        if self._snapshots_lock is None:
            self._snapshots_lock = asyncio.Lock()

        # 2. Stale-While-Revalidate pattern
        if not self._snapshots_lock.locked():
            # Nobody is fetching right now.
            if hasattr(self, "_last_snapshots_time") and self._latest_snapshots:
                if (now - self._last_snapshots_time).total_seconds() >= 10:
                    # Cache is stale. Return stale immediately, but fire a background update!
                    asyncio.create_task(self._background_update_snapshots())
                return list(self._latest_snapshots.values())
            else:
                # No cache exists. We MUST block.
                await self._background_update_snapshots()
                return list(self._latest_snapshots.values())
        else:
            # Another request is already fetching data!
            if self._latest_snapshots:
                # Return whatever stale cache we have instantly
                return list(self._latest_snapshots.values())
            
            # If cache is entirely empty (first boot), we have no choice but to wait.
            async with self._snapshots_lock:
                return list(self._latest_snapshots.values())

    def add_scan_symbol(self, symbol: str) -> None:
        self._active_symbols.add(symbol.upper())
        if hasattr(self, "_last_snapshots_time"):
            from datetime import datetime, timezone, timedelta
            self._last_snapshots_time = datetime.now(timezone.utc) - timedelta(minutes=10) # force refresh

    def remove_scan_symbol(self, symbol: str) -> None:
        if symbol.upper() in self._active_symbols:
            self._active_symbols.remove(symbol.upper())
        if symbol.upper() in self._latest_snapshots:
            del self._latest_snapshots[symbol.upper()]

    async def market_overview(self) -> MarketOverview:
        snapshots = await self.get_snapshots()
        candidates = await self.run_scan(limit=8, export_csv=False)
        sector_changes: dict[str, list[float]] = {}
        for snapshot in snapshots:
            sector_changes.setdefault(snapshot.sector, []).append(snapshot.change_percent)

        sector_scores = {
            sector: sum(values) / len(values) for sector, values in sector_changes.items() if values
        }
        strongest = [sector for sector, _ in sorted(sector_scores.items(), key=lambda item: item[1], reverse=True)[:3]]
        weakest = [sector for sector, _ in sorted(sector_scores.items(), key=lambda item: item[1])[:3]]
        nifty = self._latest_snapshots.get("NIFTY")
        nifty_trend = "bullish" if nifty and nifty.change_percent > 0.4 else "neutral"
        if nifty and nifty.change_percent < -0.4:
            nifty_trend = "bearish"

        risk_notes: list[str] = []
        if any(candidate.signal_type.value == "reversal" and candidate.score >= 55 for candidate in candidates):
            risk_notes.append("Reversal candidates are elevated; avoid weak single-confirmation trades")
        if "Banking" in weakest:
            risk_notes.append("Banking weakness may pressure index momentum")
        if not risk_notes:
            risk_notes.append("No broad-market stress signal in current snapshot")

        return MarketOverview(
            observed_at=datetime.now(timezone.utc),
            nifty_trend=nifty_trend,
            strongest_sectors=strongest,
            weakest_sectors=weakest,
            hot_symbols=[candidate.symbol for candidate in candidates[:5]],
            risk_notes=risk_notes,
        )

    async def get_market_regime(self) -> MarketRegime:
        snapshots = await self.get_snapshots()
        nifty = next((s for s in snapshots if s.symbol == "NIFTY"), None)
        if not nifty:
            return MarketRegime(regime="UNKNOWN", confidence=0)
        
        # In a full system, ATR/ADX/Advances would be calculated from index historicals
        # Using mock placeholders here since this is a demonstration module integration
        return detect_market_regime(nifty, adx=25.0, atr_percent=1.2, vix=14.5, advances=1100, declines=900)

    async def get_sector_scores(self) -> list[SectorScore]:
        snapshots = await self.get_snapshots()
        return analyze_sectors(snapshots)

    def get_event_risk(self, symbol: str) -> EventRisk:
        return evaluate_event_risk(symbol)

    async def get_portfolio_risk(self) -> PortfolioRisk:
        # Mock active positions mapping for dashboard purposes
        import asyncio
        positions = await asyncio.gather(
            self.get_position_health("BEL", "425 CE", 12.5, 14.0),
            self.get_position_health("CDSL", "1350 CE", 35.0, 31.0)
        )
        snapshots = {s.symbol: s for s in await self.get_snapshots()}
        return evaluate_portfolio_risk(positions, snapshots)

    def get_performance_metrics(self) -> PerformanceMetrics:
        return calculate_performance()

    async def get_position_health(self, symbol: str, instrument: str, entry: float, current: float) -> PositionHealth:
        snap = self._snapshot_for(symbol)
        try:
            oi, chain = await self._get_option_chain_analysis(snap)
        except Exception:
            oi, chain = None, None
        scores = self._sector_scores([snap])
        ss = scores.get(snap.sector, 50)
        return evaluate_position_health(symbol, instrument, entry, current, snap, oi, chain, ss)

    async def validate_thesis(self, symbol: str, entry: float, thesis: dict) -> ThesisValidationResult:
        snap = self._snapshot_for(symbol)
        try:
            oi, chain = await self._get_option_chain_analysis(snap)
        except Exception:
            oi, chain = None, None
        scores = self._sector_scores([snap])
        ss = scores.get(snap.sector, 50)
        return evaluate_thesis(symbol, entry, thesis, snap, oi, chain, ss)
        
    def get_option_greeks(self, symbol: str, strike: float, expiry_days: int) -> OptionGreeks:
        snap = self._snapshot_for(symbol)
        return calculate_greeks(spot=snap.last_price, strike=strike, time_to_expiry_days=expiry_days, volatility=0.20)

    async def run_scan(self, limit: int = 20, export_csv: bool = True) -> list[ScannerCandidate]:
        snapshots = await self.get_snapshots()
        candidates: list[ScannerCandidate] = []
        sector_scores = self._sector_scores(snapshots)

        for snapshot in snapshots:
            if not self._passes_broad_filter(snapshot):
                continue
            technicals = analyze_technicals(snapshot.symbol, snapshot.candles)
            if self._options_collector and settings.nse_options_chain_enabled:
                try:
                    oi_snapshot, option_chain = await self._get_option_chain_analysis(snapshot)
                except Exception as e:
                    import logging
                    logging.getLogger("uvicorn").warning(
                        f"Failed to fetch live option chain for {snapshot.symbol} during scan: {e}."
                    )
                    oi_snapshot = None
                    option_chain = None
            else:
                oi_snapshot = None
                option_chain = None

            candidate = score_candidate(
                snapshot=snapshot,
                technicals=technicals,
                oi_snapshot=oi_snapshot,
                option_chain=option_chain,
                sector_score=sector_scores.get(snapshot.sector, 50),
            )
            if candidate.score >= settings.scanner_min_score:
                candidate.evidence["ai_summary"] = explain_candidate(candidate)
                candidates.append(candidate)

        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        for rank, candidate in enumerate(candidates, start=1):
            candidate.rank = rank
        self._latest_candidates = candidates[:limit]
        if self.repository:
            self.repository.save_scanner_results(self._latest_candidates)
        if export_csv:
            self.exporter.export_candidates(self._latest_candidates)
            
        # Emit generic AI signals to Telegram (market hours only)
        self._emit_scan_alerts(self._latest_candidates)
            
        return self._latest_candidates

    def _emit_scan_alerts(self, candidates: list[ScannerCandidate]) -> None:
        if not self.telegram_enabled:
            return
            
        from zoneinfo import ZoneInfo
        from datetime import time, datetime
        
        # Only send AI signal notifications during market hours (9:15 - 15:30 IST, Mon-Fri)
        now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
        if now_ist.weekday() >= 5: # Saturday or Sunday
            return
        if not (time(9, 15) <= now_ist.time() <= time(15, 30)):
            return
            
        # 1. Route raw candidates through the Selection Engine
        selected = self.selection_engine.select_top_opportunities(candidates)
        if not selected:
            return
            
        # 2. Format a consolidated message
        regime = "SIDEWAYS" # Fallback if we don't have access to the global regime here
        if candidates:
             regime = candidates[0].regime

        lines = [
            "🎯 <b>ALPHAHUNTER — TOP F&O PICKS</b>",
            f"Market Regime: {regime}",
            f"Candidates Scanned: {len(candidates)}",
            f"Final Picks: {len(selected)}",
            "━━━━━━━━━━━━━━━━\n"
        ]
        
        medals = ["🥇", "🥈", "🥉", "🏅", "🏅", "🏅"]
        for idx, s in enumerate(selected):
            medal = medals[idx] if idx < len(medals) else "🏅"
            lines.extend([
                f"{medal} <b>{s.symbol}</b>",
                f"Alpha Score: {s.alpha_score}/100",
                f"Selection Score: {s.selection_score}/100",
                f"Direction: {s.direction}",
                f"Setup: {s.signal_type.value.replace('_', ' ').title()}",
                f"Entry: ₹{s.entry}",
                f"SL: ₹{s.sl}",
                f"Target: ₹{s.target}",
                f"RR: {s.risk_reward}",
                ""
            ])
            
        lines.append("━━━━━━━━━━━━━━━━")
        lines.append(f"Excluded: {len(candidates) - len(selected)} candidates rejected by ranking, risk, or diversification constraints.")
        
        text = "\n".join(lines)
        
        # 3. Create a pseudo-AlertMessage to satisfy the existing notifier contract
        # (Since we're sending a consolidated block, we'll wrap it in a single alert)
        from app.domain.contracts import AlertMessage, AlertType, AlertAction
        
        alert = AlertMessage(
            alert_type=AlertType.REVERSAL, # Dummy type for the consolidated message
            symbol="CONSOLIDATED",
            action=AlertAction.WATCH,
            title="AlphaHunter Top Picks",
            message=text,
            score=100.0,
            triggered_at=datetime.now(timezone.utc),
            payload={}
        )
        self._store_and_send(alert)

    async def get_ai_signals(self) -> list[TradeCard]:
        snapshots = await self.get_snapshots()
        signals = []
        sector_scores = self._sector_scores(snapshots)
            
        for snap in snapshots:
            # 1. Technical Analysis
            technicals = analyze_technicals(snap.symbol, snap.candles)
            
            # 2. Options chain analysis
            if self._options_collector and settings.nse_options_chain_enabled:
                try:
                    oi_snapshot, option_chain = await self._get_option_chain_analysis(snap)
                except Exception:
                    oi_snapshot = None
                    option_chain = None
            else:
                oi_snapshot = None
                option_chain = None
                
            # 3. Score candidate
            sec_score = sector_scores.get(snap.sector, 50.0)
            candidate = score_candidate(
                snapshot=snap,
                technicals=technicals,
                oi_snapshot=oi_snapshot,
                option_chain=option_chain,
                sector_score=sec_score
            )
            
            # 4. Generate Trade Card from ScannerCandidate
            card = generate_trade_card(candidate)
            if card.signal in ("BUY", "SELL", "WATCHLIST"):
                signals.append(card)
        
        # Sort BUY/SELL first, then by confidence
        signals.sort(key=lambda x: (0 if x.signal in ("BUY", "SELL") else 1, -x.confidence))
        
        # Telegram alerts are now strictly handled by the background SelectionEngine in `run_scan`.
        # DO NOT spam telegram every time the UI polls this endpoint.
                
        return signals

    async def get_exit_signals(self) -> list[ExitSignal]:
        exits = []
        snapshots = {s.symbol: s for s in await self.get_snapshots()}
        
        from app.engine.regime_engine import detect_market_regime
        # Mock index snap for regime
        nifty = snapshots.get("NIFTY")
        if nifty:
            regime = detect_market_regime(nifty, 25.0, 1.2, 14.5, 1100, 900).regime
        else:
            regime = "UNKNOWN"
            
        from app.engine.news_engine import analyze_news_sentiment

        for position in self._positions.values():
            if position.symbol in snapshots:
                snap = snapshots[position.symbol]
                try:
                    oi_snapshot, _ = await self._get_option_chain_analysis(snap)
                except Exception:
                    oi_snapshot = None
                    
                news_res = analyze_news_sentiment(snap.symbol, snap.observed_at)
                exit_signal = evaluate_exit(position, snap, oi_snapshot, regime, news_res.news_sentiment)
                if exit_signal.action != "HOLD":
                    exits.append(exit_signal)
                    # Telegram alerts should be handled by a stateful background task, not the UI poll
                    
        return exits

    async def add_position(self, position: PositionInput) -> PositionState:
        snapshot = self._snapshot_for(position.symbol)
        pnl_percent = ((snapshot.last_price - position.entry_price) / position.entry_price) * 100
        position_id = str(uuid4())
        state = PositionState(
            id=position_id,
            opened_at=datetime.now(timezone.utc),
            latest_price=snapshot.last_price,
            pnl_percent=round(pnl_percent, 2),
            health_score=None,
            reversal_score=None,
            action=AlertAction.HOLD,
            reasons=[],
            **position.model_dump(),
        )
        self._positions[position_id] = state
        await self.evaluate_positions()
        if self.repository:
            self.repository.save_position(self._positions[position_id])
        return self._positions[position_id]

    def remove_position(self, position_id: str) -> None:
        if position_id in self._positions:
            del self._positions[position_id]
        if self.repository:
            self.repository.delete_position(position_id)
            # Optionally remove from database if persistence is fully implemented
            if self.repository:
                try:
                    # We might not have a delete function in repository yet, but we will remove from memory
                    pass
                except Exception:
                    pass

    async def list_positions(self) -> list[PositionState]:
        await self.evaluate_positions()
        return list(self._positions.values())

    async def evaluate_positions(self) -> list[PositionState]:
        for position_id, position in list(self._positions.items()):
            await asyncio.sleep(0)  # Yield event loop to prevent starvation
            snapshot = self._snapshot_for(position.symbol)
            technicals = analyze_technicals(position.symbol, snapshot.candles)
            if self._options_collector and settings.nse_options_chain_enabled:
                try:
                    oi_snapshot, option_chain = await self._get_option_chain_analysis(snapshot)
                except Exception as e:
                    import logging
                    logging.getLogger("uvicorn").warning(
                        f"Failed to fetch live option chain for {position.symbol} during evaluation: {e}."
                    )
                    oi_snapshot = None
                    option_chain = None
            else:
                oi_snapshot = None
                option_chain = None

            reversal = assess_reversal(
                position=position,
                snapshot=snapshot,
                technicals=technicals,
                oi_snapshot=oi_snapshot,
                option_chain=option_chain,
                sector_score=self._sector_scores([snapshot]).get(snapshot.sector, 50),
            )
            latest_price = snapshot.last_price
            pnl_percent = ((latest_price - position.entry_price) / position.entry_price) * 100
            refreshed = position.model_copy(
                update={
                    "latest_price": latest_price,
                    "pnl_percent": round(pnl_percent, 2),
                    "reversal_score": reversal.score,
                    "reasons": reversal.reasons,
                    "action": reversal.action,
                }
            )
            health = score_trade_health(refreshed, reversal)
            refreshed = refreshed.model_copy(
                update={
                    "health_score": health.score,
                    "action": health.action if health.action != AlertAction.HOLD else reversal.action,
                    "reasons": health.reasons,
                }
            )
            refreshed.reasons.append(explain_trade_health(health))
            self._positions[position_id] = refreshed
            if refreshed.action in {AlertAction.REDUCE, AlertAction.EXIT}:
                self._emit_position_alert(refreshed)
            if self.repository:
                self.repository.save_position(refreshed)

        return list(self._positions.values())

    async def portfolio_summary(self) -> AlertMessage:
        positions = await self.evaluate_positions() if self._positions else await self.list_positions()
        message = summarize_portfolio(positions)
        alert = AlertMessage(
            alert_type=AlertType.PORTFOLIO_SUMMARY,
            action=AlertAction.WATCH,
            title="15-minute portfolio summary",
            message=message,
            triggered_at=datetime.now(timezone.utc),
        )
        self._store_and_send(alert)
        return alert

    async def daily_report(self) -> AlertMessage:
        overview = await self.market_overview()
        candidates = self._latest_candidates or await self.run_scan(limit=5)
        message = "\n".join(
            [
                f"NIFTY trend: {overview.nifty_trend}",
                f"Strong sectors: {', '.join(overview.strongest_sectors)}",
                f"Weak sectors: {', '.join(overview.weakest_sectors)}",
                f"Top opportunities: {', '.join(candidate.symbol for candidate in candidates[:5])}",
                f"Risk notes: {'; '.join(overview.risk_notes)}",
            ]
        )
        alert = AlertMessage(
            alert_type=AlertType.DAILY_REPORT,
            action=AlertAction.WATCH,
            title="Daily market intelligence report",
            message=message,
            triggered_at=datetime.now(timezone.utc),
        )
        self._store_and_send(alert)
        return alert

    def telegram_test(self) -> AlertMessage:
        alert = AlertMessage(
            alert_type=AlertType.PORTFOLIO_SUMMARY,
            action=AlertAction.WATCH,
            title="Telegram test alert",
            message="AlphaHunter alert pipeline is connected.",
            triggered_at=datetime.now(timezone.utc),
        )
        self._store_and_send(alert)
        return alert

    async def list_alerts(self, limit: int = 50) -> list[AlertMessage]:
        if not self._alerts:
            await self.run_scan(limit=5)
        return list(reversed(self._alerts[-limit:]))

    def backtest(self) -> BacktestMetrics:
        candles_by_symbol = {}
        for symbol in DEFAULT_SYMBOLS:
            if "NIFTY" in symbol or "BANKNIFTY" in symbol:
                continue
            try:
                snap = self.collector.snapshot_for(symbol)
                if snap and hasattr(snap, "candles") and snap.candles:
                    candles_by_symbol[symbol] = snap.candles
            except Exception:
                pass
        return run_breakout_backtest(candles_by_symbol)

    def latest_analysis_export(self) -> Path | None:
        return self.exporter.latest_file

    def list_analysis_exports(self) -> list[Path]:
        return self.exporter.list_exports()

    def get_intraday_data(self, symbol: str, interval: str) -> list[MarketCandle]:
        """Fetch real intraday data for a given symbol and interval using the active collector."""
        if not hasattr(self.collector, 'intraday_for'):
            raise NotImplementedError("Current market data provider does not support intraday_for")
            
        period_map = {
            "1m": "5d",
            "5m": "1mo",
            "15m": "1mo",
            "1h": "1mo",
            "1d": "1y",
            "1D": "1y"
        }
        
        # map generic timeframes to yfinance supported intervals
        interval_map = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "1H": "1h",
            "1h": "1h",
            "4H": "1d", # fake 4H using 1d because yf doesn't easily support 4h in all cases without extra processing
            "1D": "1d",
            "1d": "1d",
            "1W": "1wk"
        }
        
        yf_interval = interval_map.get(interval, "1d")
        period = period_map.get(yf_interval, "1mo")
        
        return self.collector.intraday_for(symbol, interval=yf_interval, period=period)

    def security_archives(
        self,
        symbol: str,
        from_date: date | None = None,
        to_date: date | None = None,
        series: str = "ALL",
        use_live: bool = False,
    ) -> list[SecurityArchiveRecord]:
        end_date = to_date or datetime.now(timezone.utc).date()
        start_date = from_date or (end_date - timedelta(days=90))
        normalized_symbol = symbol.upper()

        records: list[SecurityArchiveRecord] = []

        # ── FAST PATH: convert already-fetched in-memory candles ─────────────
        # This is INSTANT — no network call needed for tracked symbols.
        snap = self._latest_snapshots.get(normalized_symbol)
        if snap:
            if snap.candles:
                for candle in snap.candles:
                    candle_date = candle.observed_at.date()
                    if start_date <= candle_date <= end_date:
                        high_p  = candle.high
                        low_p   = candle.low
                        close_p = candle.close
                        vwap_calc = round((high_p + low_p + close_p) / 3, 2)
                        records.append(SecurityArchiveRecord(
                            symbol=normalized_symbol,
                            series=series,
                            trade_date=candle_date,
                            previous_close=candle.previous_close or close_p,
                            open_price=candle.open,
                            high_price=high_p,
                            low_price=low_p,
                            last_price=close_p,
                            close_price=close_p,
                            vwap=vwap_calc,
                            total_traded_quantity=candle.volume,
                            turnover=0.0,
                            number_of_trades=0,
                            deliverable_quantity=0,
                            delivery_to_traded_percent=candle.delivery_percent or 0.0,
                            source="memory_fast"
                        ))
                records.sort(key=lambda r: r.trade_date)
            else:
                # Snapshot exists but candles not yet loaded — synthesize a single record
                # from the snapshot live price so we still avoid a yfinance call
                p = snap.last_price
                records = [SecurityArchiveRecord(
                    symbol=normalized_symbol,
                    series=series,
                    trade_date=end_date,
                    previous_close=snap.previous_close,
                    open_price=p,
                    high_price=p,
                    low_price=p,
                    last_price=p,
                    close_price=p,
                    vwap=p,
                    total_traded_quantity=snap.volume,
                    turnover=0.0,
                    number_of_trades=0,
                    deliverable_quantity=0,
                    delivery_to_traded_percent=snap.delivery_percent or 0.0,
                    source="memory_snapshot"
                )]
            if records:
                return records


        # ⚠️ SLOW PATH: yfinance fetch (only for unknown symbols) ⚠️
        if use_live and normalized_symbol != "ETERNAL":
            try:
                import yfinance as yf
                import time as _time

                ticker_name = (
                    "^NSEI" if normalized_symbol == "NIFTY"
                    else "^NSEBANK" if normalized_symbol == "BANKNIFTY"
                    else f"{normalized_symbol}.NS"
                )

                # Service-level in-memory cache keyed by (ticker, dates)
                if not hasattr(self, "_yf_hist_cache"):
                    self._yf_hist_cache: dict = {}
                _cache_key = (ticker_name, str(start_date), str(end_date))
                _cached = self._yf_hist_cache.get(_cache_key)
                if _cached and (_time.monotonic() - _cached[0]) < 60:
                    df = _cached[1]
                else:
                    df = yf.download(
                        ticker_name,
                        start=start_date.isoformat(),
                        end=end_date.isoformat(),
                        progress=False,
                        auto_adjust=True,
                        threads=False,
                    )
                    # Flatten MultiIndex columns if present (newer yfinance)
                    import pandas as pd
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    self._yf_hist_cache[_cache_key] = (_time.monotonic(), df)

                for idx, row in df.iterrows():
                    obs_date = idx.to_pydatetime().date()
                    open_p  = float(row.get("Open",  0))
                    high_p  = float(row.get("High",  0))
                    low_p   = float(row.get("Low",   0))
                    close_p = float(row.get("Close", 0))
                    vwap_calc = round((high_p + low_p + close_p) / 3, 2)
                    records.append(SecurityArchiveRecord(
                        symbol=normalized_symbol,
                        series=series,
                        trade_date=obs_date,
                        previous_close=close_p,
                        open_price=open_p,
                        high_price=high_p,
                        low_price=low_p,
                        last_price=close_p,
                        close_price=close_p,
                        vwap=vwap_calc,
                        total_traded_quantity=int(row.get("Volume", 0)),
                        turnover=0.0,
                        number_of_trades=0,
                        deliverable_quantity=0,
                        delivery_to_traded_percent=0.0,
                        source="yfinance_fallback"
                    ))
            except Exception:
                pass

        # Last resort: demo data for symbols in active universe
        if not records:
            if self.market_data_provider == "demo" or normalized_symbol in self._active_symbols:
                records = self.demo_collector.security_archives(
                    normalized_symbol, start_date, end_date, series,
                )

        if self.repository:
            self.repository.save_security_archives(records)
        return records

    def _collect_snapshots(self) -> list[MarketSnapshot]:
        symbols_to_fetch = list(self._active_symbols)
        if isinstance(self.collector, DemoMarketDataCollector):
            snapshots = self.collector.collect_market_snapshots()
        else:
            try:
                snapshots = self.collector.collect_market_snapshots(symbols_to_fetch)
            except Exception:
                snapshots = []
            
            _ = {s.symbol.upper() for s in snapshots}
            # Skip any symbols that failed to fetch from the live market data provider (no demo fallback)
            pass

        live_map = {}
        if self._live_quote_collector:
            try:
                symbols_to_fetch = [s.symbol for s in snapshots]
                live_quotes = self._live_quote_collector.quote_all(symbols_to_fetch)
                live_map = {q.symbol.upper(): q for q in live_quotes}
            except Exception as e:
                import logging
                logging.getLogger("uvicorn").warning(f"Failed to fetch live quotes from NSE: {e}")

        # Batch fetch all missing quotes from yfinance in a single request!
        missing_symbols = [s.symbol for s in snapshots if s.symbol.upper() not in live_map]
        if missing_symbols:
            yf_quotes = _get_yfinance_quotes(missing_symbols)
            live_map.update(yf_quotes)

        # Fetch latest delivery data
        delivery_map = {}
        if self.repository:
            from app.db.session import SessionLocal
            from app.db.models.bhavcopy import BhavCopyDaily
            from sqlalchemy import select, func
            
            db = SessionLocal()
            try:
                latest_date = db.scalar(select(func.max(BhavCopyDaily.date)))
                if latest_date:
                    stmt = select(BhavCopyDaily.symbol, BhavCopyDaily.delivery_pct).where(BhavCopyDaily.date == latest_date)
                    for row in db.execute(stmt):
                        if row[0]:
                            delivery_map[row[0].upper()] = float(row[1] or 0.0)
            except Exception as e:
                import logging
                logging.getLogger("uvicorn").error(f"Failed to fetch delivery stats: {e}")
            finally:
                db.close()

        for idx, snap in enumerate(snapshots):
            symbol_upper = snap.symbol.upper()
            q = live_map.get(symbol_upper)
            deliv = delivery_map.get(symbol_upper, snap.delivery_percent)

            if q:
                updated_candles = list(snap.candles)
                if updated_candles:
                    last_candle = updated_candles[-1].model_copy(update={
                        "close": q.last_price,
                        "volume": q.volume or updated_candles[-1].volume,
                        "observed_at": q.observed_at,
                    })
                    updated_candles[-1] = last_candle

                snapshots[idx] = snap.model_copy(update={
                    "last_price": q.last_price,
                    "previous_close": q.previous_close,
                    "change_percent": q.change_percent,
                    "volume": q.volume or snap.volume,
                    "delivery_percent": deliv,
                    "observed_at": q.observed_at,
                    "candles": updated_candles,
                    "source": q.source
                })
            else:
                snapshots[idx] = snap.model_copy(update={"delivery_percent": deliv})

        return snapshots

    def _load_positions_from_storage(self) -> None:
        if not self.repository:
            return
        for position in self.repository.load_open_positions():
            self._positions[position.id] = position

    def _snapshot_for(self, symbol: str) -> MarketSnapshot:
        normalized = symbol.upper()
        if normalized not in self._latest_snapshots:
            if isinstance(self.collector, DemoMarketDataCollector):
                self._latest_snapshots[normalized] = self.collector.snapshot_for(normalized)
            else:
                self._latest_snapshots[normalized] = self.collector.snapshot_for(normalized)
        return self._latest_snapshots[normalized]

    def _passes_broad_filter(self, snapshot: MarketSnapshot) -> bool:
        volume_ratio = snapshot.volume / snapshot.average_volume_20d if snapshot.average_volume_20d else 1
        if abs(snapshot.change_percent) > 2:
            return True
        if volume_ratio > 1.6:
            return True
        if snapshot.delivery_percent and snapshot.delivery_percent > 55:
            return True
        if snapshot.symbol in {"CDSL", "BEL", "ADANIPOWER", "MCX"}:
            return True
        return False

    def _sector_scores(self, snapshots: list[MarketSnapshot]) -> dict[str, float]:
        sector_changes: dict[str, list[float]] = {}
        for snapshot in snapshots:
            sector_changes.setdefault(snapshot.sector, []).append(snapshot.change_percent)
        return {
            sector: max(0.0, min(100.0, 50 + (sum(values) / len(values)) * 8))
            for sector, values in sector_changes.items()
            if values
        }

    def _emit_position_alert(self, position: PositionState) -> None:
        alert = AlertMessage(
            alert_type=AlertType.REVERSAL,
            symbol=position.symbol,
            action=position.action,
            title=f"{position.symbol} {position.action.value.upper()} signal",
            message="\n".join(position.reasons[:4]),
            score=position.reversal_score,
            triggered_at=datetime.now(timezone.utc),
            payload=position.model_dump(mode="json"),
        )
        self._store_and_send(alert)

    def _store_and_send(self, alert: AlertMessage) -> None:
        dedupe_key = (
            alert.alert_type,
            alert.symbol,
            alert.action,
            alert.title,
            int(alert.triggered_at.timestamp() / 900),
        )
        for existing in self._alerts[-20:]:
            existing_key = (
                existing.alert_type,
                existing.symbol,
                existing.action,
                existing.title,
                int(existing.triggered_at.timestamp() / 900),
            )
            if existing_key == dedupe_key:
                return
        self._alerts.append(alert)
        if self.repository:
            self.repository.save_alert(alert)
        self.notifier.send(alert)

    # ── Live NSE data methods ─────────────────────────────────────────────────

    def get_live_quotes(self, symbols: list[str] | None = None) -> list[LiveQuote]:
        """
        Return live quotes from NSE when enabled, otherwise fallback to yfinance
        live quotes or synthesise from latest in-memory snapshots.
        """
        targets = symbols or DEFAULT_SYMBOLS
        results: list[LiveQuote] = []
        if self._live_quote_collector:
            try:
                results = self._live_quote_collector.quote_all(targets)
            except Exception as e:
                import logging
                logging.getLogger("uvicorn").warning(f"Failed to fetch live quotes from NSE: {e}. Trying Yahoo fallback.")

        retrieved = {q.symbol.upper() for q in results}
        
        # Batch fetch missing symbols from yfinance (skip ETERNAL due to YF bugs)
        missing_symbols = [s for s in targets if s.upper() not in retrieved and s.upper() != "ETERNAL"]
        if missing_symbols:
            yf_quotes = _get_yfinance_quotes(missing_symbols)
            for q in yf_quotes.values():
                results.append(q)
                retrieved.add(q.symbol.upper())

        # Fallback to demo quote if both failed, but ONLY if we are in demo mode
        # or if the symbol is part of the actively tracked symbols to avoid 
        # generating fake data for completely invalid/delisted symbols.
        for sym in targets:
            symbol_upper = sym.upper()
            if symbol_upper not in retrieved:
                if symbols or self.market_data_provider == "demo" or symbol_upper in self._active_symbols:
                    try:
                        results.append(self._get_demo_live_quote(sym))
                    except Exception:
                        pass
                        
        return results

    def _get_demo_live_quote(self, symbol: str) -> LiveQuote:
        snap = self._snapshot_for(symbol)
        return LiveQuote(
            symbol=snap.symbol,
            observed_at=snap.observed_at,
            last_price=snap.last_price,
            previous_close=snap.previous_close,
            change=snap.last_price - snap.previous_close,
            change_percent=snap.change_percent,
            volume=snap.volume,
            sector=snap.sector,
            source="demo",
        )

    async def get_option_chain(
        self,
        symbol: str,
        expiry: date | None = None,
    ) -> OptionChainFull:
        """
        Return a live options chain from NSE when enabled.
        Raises an exception if the live collection fails, ensuring NO demo data fallback.
        """
        if not self._options_collector:
            raise RuntimeError("NSE Live options chain collector is disabled or not configured in settings.")

        import asyncio
        try:
            scraper_symbol = "TMCV" if symbol.upper() == "TATAMOTORS" else ("LTM" if symbol.upper() == "LTIM" else symbol.upper())
            chain = await asyncio.to_thread(self._options_collector.get_chain, scraper_symbol, expiry)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch live option chain for {symbol} from NSE: {e}")

        if not chain:
            raise RuntimeError(f"NSE returned empty options chain data for {symbol}")

        # Set symbol back to expected name for frontend mapping
        chain.symbol = symbol.upper()

        # ── AI Options Suggestion ────────────────────────────────
        chain.ai_suggestion = self._generate_ai_option_suggestion(chain)
        return chain

    def _generate_ai_option_suggestion(self, chain: "OptionChainFull") -> OptionSuggestion:
        from app.engine.ml_model import ml_scoring_model
        
        # Get underlying snap for ML scoring
        snap = self._snapshot_for(chain.symbol)
        
        # Calculate base probability using ML engine
        volume_ratio = snap.volume / snap.average_volume_20d if snap.average_volume_20d else 1.0
        prob = ml_scoring_model.predict_probability(
            volume_ratio=volume_ratio,
            change_percent=snap.change_percent,
            last_price=snap.last_price,
            week52_high=None
        )
        
        # Determine trend based on price action and probability
        is_bullish = snap.change_percent > 0 and prob > 0.6
        is_bearish = snap.change_percent < 0 and prob > 0.6
        
        # Find ATM strike
        atm_strike = chain.atm_strike or chain.underlying_price
        
        if is_bullish:
            return OptionSuggestion(
                option_type="CE",
                suggested_strike=atm_strike,
                probability=round(prob, 2),
                signal="Bullish",
                reasoning=f"Strong upward momentum (Change: {snap.change_percent:.2f}%). Volume expansion supports Call buying.",
                entry_price_target=None
            )
        elif is_bearish:
            # For bearish, invert prob for the UI presentation (since predict_probability predicts success of long)
            bearish_prob = 1.0 - prob if prob < 0.4 else prob
            return OptionSuggestion(
                option_type="PE",
                suggested_strike=atm_strike,
                probability=round(bearish_prob, 2),
                signal="Bearish",
                reasoning=f"Downward pressure detected (Change: {snap.change_percent:.2f}%). Market structure favors Put buying.",
                entry_price_target=None
            )
        else:
            return OptionSuggestion(
                option_type="Hold",
                suggested_strike=atm_strike,
                probability=round(prob, 2),
                signal="Neutral",
                reasoning="No clear directional edge. Wait for better risk-reward setup.",
                entry_price_target=None
            )

    async def get_option_expiries(self, symbol: str) -> list[date]:
        """Return available option expiry dates for a symbol."""
        if self._options_collector:
            try:
                import asyncio
                return await asyncio.to_thread(self._options_collector.get_expiries, symbol.upper())
            except Exception as e:
                import logging
                logging.getLogger("uvicorn").warning(
                    f"Failed to fetch live option expiries for {symbol}: {e}. Falling back to demo data."
                )
        # Demo: return the single synthetic expiry
        from datetime import date as _date
        return [_date.today()]

    async def _get_option_chain_analysis(self, snapshot: MarketSnapshot) -> tuple[OiSnapshot, OptionChainAnalysis]:
        symbol = snapshot.symbol.upper()
        chain = await self.get_option_chain(symbol)

        levels = []
        total_change_oi = 0
        for strike in chain.strikes:
            levels.append(OptionLevel(
                strike_price=strike.strike_price,
                call_oi=strike.ce_oi or 0,
                put_oi=strike.pe_oi or 0,
                call_change_oi=strike.ce_change_oi or 0,
                put_change_oi=strike.pe_change_oi or 0,
            ))
            if strike.ce_change_oi is not None:
                total_change_oi += strike.ce_change_oi
            if strike.pe_change_oi is not None:
                total_change_oi += strike.pe_change_oi

        analysis = OptionChainAnalysis(
            symbol=chain.symbol,
            observed_at=chain.observed_at,
            expiry_date=chain.expiry_date,
            pcr=chain.pcr,
            max_call_oi_strike=chain.max_call_oi_strike,
            max_put_oi_strike=chain.max_put_oi_strike,
            resistance=chain.max_call_oi_strike,
            support=chain.max_put_oi_strike,
            levels=levels,
        )

        open_interest = chain.total_ce_oi + chain.total_pe_oi
        previous_oi = open_interest - total_change_oi
        if previous_oi > 0:
            oi_change_percent = (total_change_oi / previous_oi) * 100
        else:
            oi_change_percent = 0.0

        price_change = snapshot.change_percent
        if price_change > 0.5 and oi_change_percent > 0.5:
            interpretation = OiInterpretation.LONG_BUILDUP
        elif price_change < -0.5 and oi_change_percent > 0.5:
            interpretation = OiInterpretation.SHORT_BUILDUP
        elif price_change > 0.5 and oi_change_percent < -0.5:
            interpretation = OiInterpretation.SHORT_COVERING
        elif price_change < -0.5 and oi_change_percent < -0.5:
            interpretation = OiInterpretation.LONG_UNWINDING
        else:
            interpretation = OiInterpretation.NEUTRAL

        oi_snapshot = OiSnapshot(
            symbol=symbol,
            observed_at=chain.observed_at,
            price_change_percent=price_change,
            oi_change_percent=round(oi_change_percent, 2),
            open_interest=open_interest,
            interpretation=interpretation,
        )

        return oi_snapshot, analysis



trading_service = TradingService()

