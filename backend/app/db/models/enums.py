from enum import StrEnum


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    REDUCE = "reduce"
    EXIT = "exit"
    CRITICAL = "critical"


class AlertStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"


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


class ContractType(StrEnum):
    EQUITY = "equity"
    FUTURE = "future"
    OPTION = "option"
    INDEX = "index"


class InvestorType(StrEnum):
    FII = "fii"
    DII = "dii"


class MarketSegment(StrEnum):
    CASH = "cash"
    INDEX_FUTURES = "index_futures"
    INDEX_OPTIONS = "index_options"
    STOCK_FUTURES = "stock_futures"
    STOCK_OPTIONS = "stock_options"


class OiInterpretation(StrEnum):
    LONG_BUILDUP = "long_buildup"
    LONG_UNWINDING = "long_unwinding"
    SHORT_BUILDUP = "short_buildup"
    SHORT_COVERING = "short_covering"
    NEUTRAL = "neutral"


class OptionType(StrEnum):
    CALL = "CE"
    PUT = "PE"


class PositionSide(StrEnum):
    LONG = "long"
    SHORT = "short"


class PositionStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ScannerSignalType(StrEnum):
    SWING_LONG = "swing_long"
    SWING_SHORT = "swing_short"
    BREAKOUT = "breakout"
    MOMENTUM = "momentum"
    REVERSAL = "reversal"


class TradeResult(StrEnum):
    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"


class TrendDirection(StrEnum):
    STRONG_UP = "strong_up"
    UP = "up"
    SIDEWAYS = "sideways"
    DOWN = "down"
    STRONG_DOWN = "strong_down"


def enum_values(enum_type: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_type]

