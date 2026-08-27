# Development Phases

## Phase 1: Project Architecture and Folder Structure

Status: ready for review.

Deliverables:

- Repository layout
- Backend module boundaries
- Dashboard workspace placeholder
- Architecture notes
- Environment example
- Minimal FastAPI app shell

Exit criteria:

- Folder structure is clear
- Responsibilities are separated
- No later-phase implementation has been introduced
- Founder approval is received before Phase 2 begins

## Phase 2: Database Schema

Status: ready for review.

Deliverables:

- SQLAlchemy model layer
- Alembic migration setup
- Initial PostgreSQL schema migration
- Indexing strategy
- Retention strategy

Exit criteria:

- Required product tables are represented
- Snapshot tables support append-heavy writes
- Operational tables support alerts, positions, and trade history
- Schema is reviewed before collectors begin

Define PostgreSQL tables, relationships, indexes, migrations, and retention strategy.

## Phase 3: Data Collectors

Status: MVP complete.

Implement resilient source adapters for NSE, OHLC fallback data, derivatives, options, and market reports.

## Phase 4: Scanner Engine

Status: MVP complete.

Implement broad-market filtering and candidate ranking.

## Phase 5: Reversal Engine

Status: MVP complete.

Implement weighted multi-confirmation reversal scoring.

## Phase 6: Telegram Alerts

Status: MVP complete.

Implement instant alerts, 15-minute summaries, and daily reports.

## Phase 7: Dashboard

Status: MVP complete.

Build the web dashboard for market overview, scanner, open trades, alerts, and analytics.

## Phase 8: AI Reasoning Engine

Status: MVP complete.

Add explanation, ranking commentary, and conflict detection over structured signals.

## Phase 9: Backtesting Engine

Status: MVP complete.

Replay historical sessions and calculate validation metrics.

## Phase 10: Optimization and SaaS Scaling

Status: MVP foundation complete.

Improve performance, isolation, observability, deployment, and multi-user readiness.
