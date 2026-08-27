# AlphaHunter Runbook

This repository now runs as a local end-to-end MVP for AlphaHunter. It uses deterministic demo market data by default so the scanner, reversal engine, alerts, dashboard, AI commentary, CSV exports, and backtest surface work without paid APIs or live NSE access.

## Start Backend and Dashboard

```powershell
cd D:\internshalla\backend
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Or from the repository root:

```powershell
.\scripts\start_backend.ps1
```

Open:

```text
http://127.0.0.1:8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

## Useful Endpoints

- `GET /api/health`
- `GET /api/ready`
- `GET /api/market/overview`
- `GET /api/market/snapshots`
- `GET /api/market/security-archives?symbol=RELIANCE&range=3M&series=ALL`
- `GET /api/exports/latest`
- `GET /api/scanner/latest?limit=20`
- `POST /api/scanner/run?limit=20`
- `GET /api/positions`
- `POST /api/positions`
- `POST /api/positions/evaluate`
- `GET /api/alerts`
- `POST /api/alerts/portfolio-summary`
- `POST /api/alerts/telegram-test`
- `POST /api/reports/daily`
- `POST /api/reports/backtest`

## Enable PostgreSQL Persistence

Create and migrate the database:

```powershell
.\scripts\setup_database.ps1
```

Set this in `.env`:

```text
DATABASE_ENABLED=true
```

When enabled, the app persists stocks, market snapshots, scanner results, positions, and alerts.

## CSV Exports

Every analysis run writes a fresh CSV file to `data/exports/analysis/`.

Use the dashboard button or download the latest file directly:

```text
GET /api/exports/latest
```

The export includes ranked scanner candidates, score breakdowns, and the key evidence used for the analysis.

## NSE Security-Wise Archives

The screenshot data is available through:

```text
GET /api/market/security-archives?symbol=RELIANCE&range=3M&series=ALL
```

By default it uses deterministic demo records. Add `live=true` to call NSE:

```text
GET /api/market/security-archives?symbol=RELIANCE&from_date=2026-03-24&to_date=2026-06-24&series=ALL&live=true
```

This captures price, volume, VWAP, number of trades, deliverable quantity, and delivery percentage.

## Enable Scheduler

Set this in `.env`:

```text
START_SCHEDULER=true
```

The scheduler runs scanner and portfolio-summary jobs every `MARKET_SCAN_INTERVAL_MINUTES`.

## Stop Backend

```powershell
.\scripts\stop_backend.ps1
```

## Enable Telegram

Set these in `.env`:

```text
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

If these values are empty, alerts are stored in memory but not sent.

## Current Limits

- Demo data is active by default so the MVP is runnable immediately.
- NSE and yfinance adapters exist, but the production collector orchestration still needs hardening before relying on live trading data.
- Database schema and migrations exist, but the MVP service currently stores runtime state in memory.
- Backtesting is a first-pass breakout replay, not yet a full portfolio simulation with slippage, brokerage, expiry behavior, and options Greeks.
