# Architecture

## System Shape

The platform is structured as a modular monolith for V1. That keeps local development simple while preserving boundaries that can later be split into workers, services, or cloud jobs.

## Data Flow

```text
External data sources
  -> collectors
  -> normalized snapshots
  -> database
  -> scanners
  -> deterministic engines
  -> alerts, dashboard, AI analyst
```

## Bounded Areas

- Collection: fetch, retry, cache, rate-limit, normalize, and store source data
- Persistence: PostgreSQL tables, indexes, migrations, and query patterns
- Scanning: reduce the full NSE universe to a smaller candidate set
- Deep analysis: compute technical, cash, derivatives, and options context
- Reversal detection: score deterioration across independent confirmations
- Position guarding: monitor manually entered trades against current risk
- Notification: deliver instant, periodic, and daily Telegram messages
- Dashboard: expose operational views for scanning, trades, alerts, and analytics
- AI analyst: explain structured facts without directly creating trade signals
- Backtesting: replay historical sessions and measure precision, recall, and drawdown

## Core Design Decisions

### Modular monolith first

V1 should run locally on a Windows laptop. A modular monolith avoids distributed-system overhead while still allowing later extraction of collectors, schedulers, and alert workers.

### PostgreSQL as source of truth

Market snapshots, positions, alerts, scanner results, and historical trades should land in PostgreSQL. This supports later analytics, backtesting, and SaaS reporting.

### Rules before AI

Trading signals must be deterministic, inspectable, and backtestable. AI should summarize, rank, and flag conflicts after rules produce structured evidence.

### Multi-stage scanning

The full NSE universe is too large for heavy analysis every cycle. The scanner should first shortlist candidates using cheap filters, then run expensive analysis only on selected symbols.

### Data source abstraction

NSE, TradingView-compatible sources, yfinance, and future paid providers should sit behind adapter interfaces. This prevents vendor lock-in and keeps paid API upgrades clean.

## Phase 1 Tradeoffs

- The app shell includes only a health endpoint so the backend boundary is testable.
- Database models are intentionally not created yet because schema design is Phase 2.
- Dashboard code is not scaffolded yet because UI contracts depend on later backend outputs.
- Docker assets are reserved for later infrastructure work to avoid pretending deployment is solved too early.

