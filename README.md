# AlphaHunter

Production-oriented architecture for AlphaHunter, an AI-assisted trading intelligence platform for Indian markets.

This repository now includes a local end-to-end MVP for AlphaHunter. It runs with deterministic demo market data by default, so the scanner, position guardian, reversal engine, Telegram alert wiring, dashboard, AI commentary, CSV exports, and backtest surface can be exercised without paid APIs.

## Product Goal

Build a local-first platform that can later become a cloud-deployable SaaS product for:

- Complete NSE universe scanning
- Swing and momentum opportunity detection
- Active trade monitoring
- Reversal risk detection before premium collapse
- Telegram alerts
- Dashboard analytics
- Historical learning and backtesting

## Architecture Position

The platform uses a hybrid decision model:

- 70% deterministic rules engine for signals, scoring, thresholds, and risk checks
- 30% AI reasoning engine for explanation, conflict detection, ranking commentary, and summarization

AI should not directly create buy or sell signals. It should consume structured outputs from rules and data pipelines.

## Repository Map

```text
backend/
  app/
    api/          FastAPI routes and request/response boundary
    core/         App settings, constants, runtime configuration
    db/           Database connection and migrations in later phases
    collectors/   NSE, OHLC, derivatives, options, and fallback data adapters
    scanners/     Broad market filters and candidate selection
    engine/       Scoring, reversal, trade health, and backtest engines
    ai/           AI analyst layer over structured signals
    alerts/       Telegram and notification orchestration
    scheduler/    Market-hours jobs and recurring workflows
    utils/        Shared utilities with no domain ownership
    domain/       Shared domain types and contracts
  tests/

frontend/
  dashboard/      Future Next.js dashboard workspace

docs/             Architecture and phase documentation
infra/            Deployment and local infrastructure assets
scripts/          Developer and operations scripts
data/             Local runtime data, cache, and exports
```

## Backend Migration

From `backend/`:

```powershell
alembic upgrade head
```

## Run The MVP

From `backend/`:

```powershell
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

See `docs/mvp-runbook.md` for endpoints and operating notes.

## Production Readiness Switches

- `DATABASE_ENABLED=true` persists snapshots, scanner results, positions, and alerts to PostgreSQL.
- `MARKET_DATA_PROVIDER=yfinance` uses yfinance for OHLC prices with demo derivatives fallback.
- `START_SCHEDULER=true` enables recurring scan and portfolio-summary jobs.
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` enable Telegram delivery.

Security-wise NSE archive data is exposed at `/api/market/security-archives`.

## Phase Gates

Work should proceed strictly by phase:

1. Project architecture and folder structure
2. Database schema
3. Data collectors
4. Scanner engine
5. Reversal engine
6. Telegram alerts
7. Dashboard
8. AI reasoning engine
9. Backtesting engine
10. Optimization and SaaS scaling

Each phase should end with an explanation, design decisions, tradeoffs, and approval before continuing.

## Local Stack Direction

- Backend: Python 3.11+, FastAPI, SQLAlchemy, Pandas, NumPy, APScheduler
- Database: PostgreSQL
- Optional cache: Redis
- Frontend: Next.js for SaaS-ready dashboard development
- Alerts: Telegram bot integration
- Deployment path: local first, then AWS, Render, Railway, or VPS
