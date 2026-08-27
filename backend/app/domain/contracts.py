from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AlertAction(StrEnum):
    HOLD = "hold"
    WATCH = "watch"
    REDUCE = "reduce"
    EXIT = "exit"


class AlertType(StrEnum):
    SWING_ENTRY = "swing_entry"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"
    LONG_BUILDUP = "long_buildup"
    SHORT_BUILDUP = "short_buildup"
    SECTOR_ROTATION = "sector_rotation"
    INSTITUTIONAL_FLOW = "institutional_flow"
    PORTFOLIO_SUMMARY = "portfolio_summary"
    DAILY_REPORT = "daily_report"


class InstrumentType(StrEnum):
    EQUITY = "equity"
    FUTURE = "future"
    OPTION = "option"
    INDEX = "index"


class OptionType(StrEnum):
    CALL = "CE"
    PUT = "PE"


class OiInterpretation(StrEnum):
    LONG_BUILDUP = "long_buildup"
    LONG_UNWINDING = "long_unwinding"
    SHORT_BUILDUP = "short_buildup"
    SHORT_COVERING = "short_covering"
    NEUTRAL = "neutral"


class SignalType(StrEnum):
    SWING_LONG = "swing_long"
    SWING_SHORT = "swing_short"
    BREAKOUT = "breakout"
    MOMENTUM = "momentum"
    REVERSAL = "reversal"


class CyclePhase(StrEnum):
    ACCUMULATION = "accumulation"
    MARKUP = "markup"
    DISTRIBUTION = "distribution"
    MARKDOWN = "markdown"


class VolumeTrend(StrEnum):
    RISING = "rising"
    FALLING = "falling"
    FLAT = "flat"


class BreakoutStatus(StrEnum):
    WAITING = "Waiting"
    NEAR_BREAKOUT = "Near Breakout"
    BREAKING = "Breaking"
    CONFIRMED_BREAKOUT = "Confirmed Breakout"
    RETESTING_BREAKOUT = "Retesting Breakout"
    FAKEOUT_RISK = "Fakeout Risk"
    SUPPORT_BUILDING = "Support Building"
    SUPPORT_CONFIRMED = "Support Confirmed"


class MarketCandle(BaseModel):
    symbol: str
    observed_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    previous_close: float | None = None
    delivery_percent: float | None = None


class CycleMetrics(BaseModel):
    phase: CyclePhase
    confidence: float
    probability_modifier: int


class MarketSnapshot(BaseModel):
    symbol: str
    observed_at: datetime
    last_price: float
    previous_close: float
    change_percent: float
    volume: int
    average_volume_20d: int
    delivery_percent: float | None = None
    sector: str = "Unknown"
    candles: list[MarketCandle] = Field(default_factory=list)
    source: str = "demo"
    cycle_metrics: CycleMetrics | None = None


class SecurityArchiveRecord(BaseModel):
    symbol: str
    series: str
    trade_date: date
    previous_close: float | None = None
    open_price: float | None = None
    high_price: float | None = None
    low_price: float | None = None
    last_price: float | None = None
    close_price: float | None = None
    vwap: float | None = None
    total_traded_quantity: int | None = None
    turnover: float | None = None
    number_of_trades: int | None = None
    deliverable_quantity: int | None = None
    delivery_to_traded_percent: float | None = None
    source: str = "nse_security_archives"


class OiSnapshot(BaseModel):
    symbol: str
    observed_at: datetime
    price_change_percent: float
    oi_change_percent: float
    open_interest: int
    interpretation: OiInterpretation


class OptionLevel(BaseModel):
    strike_price: float
    call_oi: int
    put_oi: int
    call_change_oi: int = 0
    put_change_oi: int = 0


class OptionChainAnalysis(BaseModel):
    symbol: str
    observed_at: datetime
    expiry_date: date | None = None
    pcr: float
    max_call_oi_strike: float | None = None
    max_put_oi_strike: float | None = None
    resistance: float | None = None
    support: float | None = None
    levels: list[OptionLevel] = Field(default_factory=list)


class TechnicalAnalysis(BaseModel):
    symbol: str
    # EMAs
    ema_20: float | None = None
    ema_50: float | None = None
    ema_100: float | None = None
    ema_200: float | None = None
    # Momentum
    rsi_14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    adx: float | None = None
    # Volatility
    atr_14: float | None = None
    bb_upper: float | None = None
    bb_lower: float | None = None
    bb_middle: float | None = None
    bb_width: float | None = None
    # Price levels
    support: float | None = None
    resistance: float | None = None
    week52_high: float | None = None
    week52_low: float | None = None
    # Trend + quality
    trend: str = "unknown"
    volume_trend: VolumeTrend = VolumeTrend.FLAT
    breakout_quality: float = 0.0


class ScannerCandidate(BaseModel):
    symbol: str
    signal_type: SignalType
    score: float
    rank: int | None = None
    price_breakout_score: float = 0.0
    oi_score: float = 0.0
    volume_score: float = 0.0
    futures_premium_score: float = 0.0
    rsi_score: float = 0.0
    option_chain_score: float = 0.0
    sector_strength_score: float = 0.0
    macd_score: float = 0.0
    bb_score: float = 0.0
    proximity_score: float = 0.0
    # New Institutional Engines
    ml_score: float = 0.0
    trend_score: float = 0.0
    options_score: float = 0.0
    cycle_score: float = 0.0
    pattern_memory_score: float = 0.0
    delivery_score: float = 0.0
    fib_score: float = 0.0
    spurt_score: float = 0.0
    structure_score: float = 0.0
    execution_score: float = 0.0
    
    signal_tier: str = "Ignore"
    regime: str = "SIDEWAYS"
    
    last_price: float | None = None
    change_percent: float | None = None
    candles: list[MarketCandle] = Field(default_factory=list)
    
    reasons: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)


class SelectedCandidate(BaseModel):
    """
    A final selected candidate that has passed the Selection Engine filtering.
    """
    symbol: str
    signal_type: SignalType
    direction: str # "LONG" or "SHORT"
    alpha_score: float
    selection_score: float
    entry: float
    sl: float
    target: float
    risk_reward: float
    setup_notes: list[str] = Field(default_factory=list)

class PositionInput(BaseModel):
    symbol: str
    instrument_type: InstrumentType = InstrumentType.EQUITY
    side: str = "long"
    quantity: int = 1
    entry_price: float
    stop_loss: float | None = None
    target_price: float | None = None
    option_type: OptionType | None = None
    strike_price: float | None = None
    expiry_date: date | None = None
    thesis: str | None = None


class BreakoutRadarCandidate(BaseModel):
    symbol: str
    last_price: float
    prev_month_high: float
    prev_month_low: float
    prev_level_date: datetime | None = None
    prev_high_date: datetime | None = None
    prev_low_date: datetime | None = None
    days_since_prev_level: int | None = None
    monthly_range: float
    distance_percent: float
    breakout_percentage: float = 0.0
    support_percentage: float = 0.0
    volume_ratio: float = 0.0
    prev_level_volume: int | None = None
    relative_strength: float = 0.0
    status: BreakoutStatus
    trend_15m: str = "Neutral"
    ema_9_status: str
    ema_9: float
    ema_20: float
    vwap: float
    volume: int
    avg_volume: int
    volume_spike_percent: float
    atr: float
    rsi: float
    adx: float
    institutional_activity_score: int = 0
    trend_strength: int = 0
    signal_strength: str = "Neutral"
    confidence_score: int = 0
    risk_reward_ratio: float
    recommended_entry: str | None = None
    stoploss: float | None = None
    target_1: float | None = None
    target_2: float | None = None
    target_3: float | None = None
    signal: str
    ai_explanation: str


class PositionState(PositionInput):
    id: str
    opened_at: datetime
    latest_price: float | None = None
    pnl_percent: float | None = None
    health_score: float | None = None
    reversal_score: float | None = None
    action: AlertAction = AlertAction.HOLD
    reasons: list[str] = Field(default_factory=list)


class ReversalAssessment(BaseModel):
    symbol: str
    score: float
    action: AlertAction
    reasons: list[str]
    evidence: dict[str, Any] = Field(default_factory=dict)


class TradeHealth(BaseModel):
    symbol: str
    score: float
    action: AlertAction
    reasons: list[str]


class AlertMessage(BaseModel):
    alert_type: AlertType
    symbol: str | None = None
    action: AlertAction = AlertAction.WATCH
    title: str
    message: str
    score: float | None = None
    triggered_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class BacktestMetrics(BaseModel):
    trades: int
    win_rate: float
    precision: float
    recall: float
    false_positive_rate: float
    sharpe_ratio: float
    max_drawdown: float
    total_return_percent: float
    # Enhanced metrics
    avg_return_per_trade: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    slippage_applied_percent: float = 0.0
    brokerage_per_leg: float = 0.0


class MarketOverview(BaseModel):
    observed_at: datetime
    nifty_trend: str
    strongest_sectors: list[str]
    weakest_sectors: list[str]
    hot_symbols: list[str]
    risk_notes: list[str]


class LiveQuote(BaseModel):
    """Real-time quote from NSE or yfinance."""
    symbol: str
    observed_at: datetime
    last_price: float
    previous_close: float
    change: float
    change_percent: float
    open: float | None = None
    high: float | None = None
    low: float | None = None
    vwap: float | None = None
    volume: int | None = None
    total_buy_quantity: int | None = None
    total_sell_quantity: int | None = None
    upper_circuit: float | None = None
    lower_circuit: float | None = None
    week52_high: float | None = None
    week52_low: float | None = None
    sector: str = "Unknown"
    source: str = "nse_live"


# ── AlphaHunter Signal Engine Pro Models ──────────────────────

class TrendResult(BaseModel):
    trend: str             # "BULLISH", "BEARISH", "NEUTRAL"
    strength: int          # 0-100

class SMCResult(BaseModel):
    smc_score: int         # 0-100
    signal: str            # "BULLISH_BOS", "BEARISH_BOS", "NEUTRAL"
    
class FibResult(BaseModel):
    fib_zone: str          # "0.618", "0.5", "NONE"
    confluence: bool
    score: int             # 0-100
    
class SessionResult(BaseModel):
    session_quality: str   # "HIGH", "MODERATE", "LOW"
    score: int             # 0-100
    
class NewsResult(BaseModel):
    news_sentiment: str    # "BULLISH", "BEARISH", "NEUTRAL"
    score: int             # 0-100

class TradeCard(BaseModel):
    symbol: str
    signal: str            # "BUY", "SELL", "WAIT"
    entry: str             # e.g., "430-432"
    stop_loss: float
    targets: list[float]
    confidence: int        # 0-100
    risk_reward: float
    reason: list[str]
    options_recommendation: str | None = None
    cycle: str = "UNKNOWN"
    cycle_confidence: float = 0.0
    risk_score: float = 0.0
    reward_score: float = 0.0
    probability: float = 0.5
    holding_period: str = "3-5 sessions"
    ai_explanation: str = ""
    technical_reasons: list[str] = Field(default_factory=list)
    options_reasons: list[str] = Field(default_factory=list)
    volume_reasons: list[str] = Field(default_factory=list)
    smart_money_reasons: list[str] = Field(default_factory=list)
    historical_similarity: dict[str, Any] = Field(default_factory=dict)
    sector_strength: float = 50.0
    news_sentiment: str = "NEUTRAL"
    market_regime: str = "SIDEWAYS"

class ExitSignal(BaseModel):
    symbol: str
    action: str            # "HOLD", "PARTIAL BOOK", "FULL EXIT"
    reason: str

# ── Phase 1: Thesis Invalidation Engine ───────────────────────
class ThesisValidationResult(BaseModel):
    status: str            # "VALID", "WEAKENING", "BROKEN"
    confidence: int        # 0-100
    reasons: list[str]
    action: str            # "HOLD", "REDUCE", "EXIT"


# ── Phase 2: Position Monitoring Engine ───────────────────────
class PositionHealth(BaseModel):
    symbol: str
    instrument: str | None = None
    entry_price: float
    current_price: float
    pnl: float
    health_score: int      # 0-100
    reversal_risk: str     # "LOW", "MEDIUM", "HIGH"


# ── Phase 3: Full Greeks Engine ───────────────────────────────
class OptionGreeks(BaseModel):
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    iv_percentile: float | None = None
    iv_rank: float | None = None

class PremiumBehavior(BaseModel):
    premium_behavior: str
    reason: list[str]


# ── Phase 4: Sector Rotation Engine ───────────────────────────
class SectorScore(BaseModel):
    sector: str
    score: int             # 0-100


# ── Phase 5: Market Regime Detection ──────────────────────────
class MarketRegime(BaseModel):
    regime: str            # "TRENDING_BULLISH", "TRENDING_BEARISH", "RANGEBOUND", "VOLATILE", "MEAN_REVERTING"
    confidence: int        # 0-100


# ── Phase 6: Event Risk Engine ────────────────────────────────
class EventRisk(BaseModel):
    symbol: str
    event_risk: str        # "LOW", "MODERATE", "HIGH", "CRITICAL"
    event: str


# ── Phase 7: Portfolio Risk Manager ───────────────────────────
class PortfolioRisk(BaseModel):
    portfolio_risk: str    # "LOW", "MODERATE", "HIGH"
    suggested_allocation: dict[str, float]


# ── Phase 8: Performance Analytics ────────────────────────────
class PerformanceMetrics(BaseModel):
    win_rate: float
    avg_rr: float
    expectancy: float
    max_drawdown: float
    profit_factor: float
    sharpe_ratio: float
    sortino_ratio: float

class OptionStrike(BaseModel):
    """Single strike row in an options chain — both CE and PE sides."""
    strike_price: float
    expiry_date: date
    is_atm: bool = False
    is_max_pain: bool = False

    # ── Call side ─────────────────────────────────────────────
    ce_ltp: float | None = None
    ce_oi: int | None = None
    ce_change_oi: int | None = None
    ce_volume: int | None = None
    ce_iv: float | None = None
    ce_bid: float | None = None
    ce_ask: float | None = None
    ce_delta: float | None = None
    ce_change_percent: float | None = None

    # ── Put side ──────────────────────────────────────────────
    pe_ltp: float | None = None
    pe_oi: int | None = None
    pe_change_oi: int | None = None
    pe_volume: int | None = None
    pe_iv: float | None = None
    pe_bid: float | None = None
    pe_ask: float | None = None
    pe_delta: float | None = None
    pe_change_percent: float | None = None

    # ── Derived ───────────────────────────────────────────────
    pcr_at_strike: float | None = None   # PE OI / CE OI at this strike
    net_oi_pressure: int | None = None    # CE change OI - PE change OI


class OptionSuggestion(BaseModel):
    """AI-driven trade suggestion for an options chain."""
    option_type: str                  # "CE" or "PE"
    suggested_strike: float           # The recommended strike price
    probability: float                # Win probability e.g. 0.88 for 88%
    signal: str                       # e.g., "Bullish", "Bearish"
    reasoning: str                    # Explanation based on AlphaHunter system
    entry_price_target: float | None = None


class OptionChainFull(BaseModel):
    """Complete options chain snapshot for one symbol + expiry."""
    symbol: str
    observed_at: datetime
    underlying_price: float
    expiry_date: date
    expiry_dates: list[date] = Field(default_factory=list)

    # ── Aggregate metrics ─────────────────────────────────────
    pcr: float                            # Total PE OI / Total CE OI
    max_pain: float | None = None         # Strike with max loss for buyers
    max_call_oi_strike: float | None = None  # Resistance wall
    max_put_oi_strike: float | None = None   # Support wall
    total_ce_oi: int = 0
    total_pe_oi: int = 0
    total_ce_volume: int = 0
    total_pe_volume: int = 0
    atm_iv: float | None = None           # IV at ATM strike (avg CE+PE)
    atm_strike: float | None = None

    # ── Strike rows (typically 20 strikes around ATM) ─────────
    strikes: list[OptionStrike] = Field(default_factory=list)

    # ── AI Recommendation ─────────────────────────────────────
    ai_suggestion: OptionSuggestion | None = None

    source: str = "nse_live"
