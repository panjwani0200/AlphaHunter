from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import sys
import os

def get_default_db_url() -> str:
    if getattr(sys, 'frozen', False):
        # TRUE PORTABLE MODE
        base_dir = os.path.dirname(sys.executable)
        db_path = os.path.join(base_dir, "alphahunter.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return f"sqlite:///{db_path}"
    # Ensure local directory exists in dev mode too
    os.makedirs(os.path.abspath(os.path.join(BACKEND_ROOT, "..", "database")), exist_ok=True)
    return f"sqlite:///{os.path.abspath(os.path.join(BACKEND_ROOT, '..', 'database', 'alphahunter.db'))}"



PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "AlphaHunter"
    app_env: str = "local"
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # Database
    database_url: str = Field(default_factory=get_default_db_url)
    database_enabled: bool = True
    database_connect_timeout_seconds: int = 5

    # Cache
    redis_url: str | None = None

    # Telegram
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    # Market data
    market_data_provider: Literal["demo", "yfinance"] = "yfinance"
    demo_seed_positions: bool = False
    nse_request_timeout_seconds: int = 20
    nse_rate_limit_per_minute: int = 30

    # Scheduler
    market_scan_interval_minutes: int = 15
    start_scheduler: bool = True

    # Scanner thresholds
    scanner_min_score: float = 25.0
    scanner_symbol_count: int = 13

    # AI commentary (optional LLM upgrade)
    gemini_api_key: str | None = None
    openai_api_key: str | None = None

    # Backtest simulation parameters
    backtest_capital: float = 100_000.0          # ₹1,00,000 starting capital
    backtest_slippage_percent: float = 0.05      # 0.05% slippage per fill
    backtest_brokerage_per_leg: float = 20.0     # ₹20 flat per leg (Zerodha model)

    # ── Live NSE data (opt-in) ─────────────────────────────────────
    nse_live_quotes_enabled: bool = False        # Pull real-time quotes from nseindia.com
    nse_options_chain_enabled: bool = False      # Pull live options chain from nseindia.com
    nse_cache_ttl_seconds: int = 60              # In-process cache TTL for live NSE responses
    nse_fno_symbols: list[str] = []              # Override symbols for F&O/options fetch
                                                 # (empty = use DEFAULT_SYMBOLS that have F&O)

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"),
        extra="ignore",
    )


settings = Settings()
