from pydantic import BaseModel, Field
from typing import Optional, List, Any

# ==========================================
# Outperform Main Dashboard Models
# ==========================================

class MarketHealth(BaseModel):
    sentiment: str = Field(..., description="Bullish, Neutral, or Bearish")
    confidence_score: int = Field(..., description="Overall market health score 0-100")
    best_sector: str = Field(...)
    weakest_sector: str = Field(...)
    sector_heatmap: dict[str, float] = Field(default_factory=dict, description="Maps sector names to their change percentage")
    advance_decline_ratio: float = Field(...)
    india_vix: float = Field(...)
    nifty_trend: str = Field(...)
    bank_nifty_trend: str = Field(...)
    fii_activity: str = Field(...)
    dii_activity: str = Field(...)
    overall_market_score: int = Field(...)

class TopAiPick(BaseModel):
    symbol: str = Field(...)
    futures_symbol: str = Field(...)
    overall_score: int = Field(..., ge=0, le=100)
    outperform_probability_pct: float = Field(...)
    bias: str = Field(..., description="LONG or SHORT")
    confidence: str = Field(...)
    sector: str = Field(...)
    current_price: float = Field(...)
    today_change_pct: float = Field(...)
    volume: int = Field(...)
    oi_change_pct: float = Field(...)
    vwap_status: str = Field(...)
    breakout_status: str = Field(...)
    ai_recommendation: str = Field(...)

class OutperformDashboardResponse(BaseModel):
    market_health: MarketHealth
    top_picks: List[TopAiPick]
    watch_list: List[str] = []
    recently_triggered: List[str] = []

# ==========================================
# Detailed Analysis Engines
# ==========================================

class TrendEngine(BaseModel):
    daily_trend: str
    weekly_trend: str
    monthly_trend: str
    trend_strength: str
    trend_continuation: str

class PriceActionEngine(BaseModel):
    higher_high: bool
    higher_low: bool
    opening_range_breakout: bool
    gap_analysis: str
    breakout: str
    retest: str
    support: float
    resistance: float

class VolumeEngine(BaseModel):
    volume_spike: bool
    relative_volume: float
    average_volume: int
    delivery_percent: float
    institutional_volume: str

class FuturesEngine(BaseModel):
    open_interest: int
    oi_change_pct: float
    long_buildup: bool
    short_buildup: bool
    long_unwinding: bool
    short_covering: bool
    oi_trend: str
    basis: float

class OptionChainEngine(BaseModel):
    pcr: float
    max_pain: float
    call_writing: str
    put_writing: str
    oi_distribution: str
    iv: float
    iv_rank: float
    option_bias: str

class SmartMoneyEngine(BaseModel):
    bulk_deals: str
    block_deals: str
    fii: str
    dii: str
    institutional_buying: bool
    institutional_selling: bool

class MomentumEngine(BaseModel):
    rsi: float
    macd: float
    adx: float
    supertrend: str
    ema: str
    vwap: float
    atr: float
    momentum_score: int

class RelativeStrengthEngine(BaseModel):
    compare_nifty: str
    compare_bank_nifty: str
    compare_sector: str
    compare_peers: str

class LiquidityEngine(BaseModel):
    bid_ask_spread: float
    market_depth: str
    slippage_estimate: str
    avg_traded_quantity: int

class VolatilityEngine(BaseModel):
    atr: float
    range_expansion: str
    volatility_score: int

class NewsEngine(BaseModel):
    recent_news: List[str]
    corporate_announcements: List[str]
    orders: str
    results: str
    management_commentary: str
    ai_news_sentiment: str

class SectorEngine(BaseModel):
    sector_rank: int
    sector_rotation: str
    sector_strength: str
    sector_momentum: str

class MarketBreadthEngine(BaseModel):
    advance_decline: str
    participation: str
    sector_breadth: str

class RiskEngine(BaseModel):
    support_levels: List[float]
    resistance_levels: List[float]
    gap_risk: str
    event_risk: str
    stoploss_risk: str
    drawdown_probability: str

class TradePlan(BaseModel):
    aggressive_entry: float
    conservative_entry: float
    pullback_entry: float
    breakout_entry: float
    suggested_stoploss: float
    target_1: float
    target_2: float
    target_3: float
    risk_reward_ratio: float

class OutperformAnalysisResponse(BaseModel):
    symbol: str
    overall_score: int
    probability_score: float
    trade_health_score: int
    trade_health_status: str
    ai_summary: str
    
    trend: TrendEngine
    price_action: PriceActionEngine
    volume: VolumeEngine
    futures: FuturesEngine
    option_chain: OptionChainEngine
    smart_money: SmartMoneyEngine
    momentum: MomentumEngine
    relative_strength: RelativeStrengthEngine
    liquidity: LiquidityEngine
    volatility: VolatilityEngine
    news: NewsEngine
    sector: SectorEngine
    market_breadth: MarketBreadthEngine
    risk: RiskEngine
    trade_plan: TradePlan
