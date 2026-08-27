# Database Schema

Phase 2 defines the PostgreSQL persistence layer for market snapshots, positions, alerts, scanner output, and learning data.

## Migration Entry Point

Run migrations from the backend directory:

```powershell
alembic upgrade head
```

The initial migration enables `pgcrypto` for UUID generation and creates database-level `updated_at` triggers.

## Core Tables

### `stocks`

Instrument master for NSE underlyings. Despite the table name, this also supports indices so option chains and index derivatives share the same reference pattern.

Key fields:

- `symbol`, `nse_symbol`, `isin`
- `instrument_type`
- `sector`, `industry`
- `lot_size`, `tick_size`
- `is_fno`, `is_active`

### `market_snapshots`

OHLC, volume, delivery, gap, ATR, and raw market activity snapshots.

Optimized for:

- symbol/time lookups
- 15-minute and daily candles
- broad scanner pre-filters
- append-heavy writes

### `option_chain_snapshots`

Strike-wise option chain snapshots by underlying, expiry, strike, and option type.

Designed for:

- call writing and put writing analysis
- support/resistance extraction
- PCR and max-pain metadata
- later Greeks enrichment

### `oi_snapshots`

Futures/options open interest snapshots and derived OI interpretation.

Stores the matrix needed for:

- long build-up
- long unwinding
- short build-up
- short covering

### `positions`

Manually entered active trades and holdings. This supports the future Position Guardian and Trade Health Engine.

Important fields:

- `entry_price`, `stop_loss`, `target_price`
- `latest_health_score`
- `latest_reversal_score`
- `thesis`

### `alerts`

Notification ledger for Telegram and future channels.

Includes:

- alert type
- severity
- status
- dedupe key
- structured payload

### `trade_history`

Closed-trade history for the later Learning Engine.

Tracks:

- setup type
- PnL
- result
- entry/exit reasons
- excursions
- lessons

### `scanner_results`

Ranked scanner output per scan run.

Stores component scores for the requested 100-point framework:

- price breakout
- OI
- volume
- futures premium
- RSI
- option chain
- sector strength

### `sector_strength`

Sector rotation and relative strength snapshots.

### `fii_data`

FII and optional DII flow by market segment.

## Indexing Strategy

- Time-series tables use `(symbol, observed_at)` or equivalent lookup indexes.
- High-volume snapshot tables use BRIN indexes on timestamp columns.
- Alert and position tables are indexed by operational access patterns.
- Uniqueness constraints prevent duplicate source snapshots for the same timestamp and contract.

## Retention Strategy

Suggested V1 retention:

- Intraday `market_snapshots`: 180 days locally, then aggregate or archive
- `option_chain_snapshots`: 90 to 180 days because volume grows quickly
- `oi_snapshots`: 180 days for reversal and derivatives research
- `scanner_results`: 365 days for strategy tuning
- `alerts`, `positions`, `trade_history`: retain indefinitely
- `fii_data`, `sector_strength`: retain indefinitely

Monthly partitioning should be introduced when snapshot tables become large enough to slow local queries or backups. It is intentionally deferred until collector write volume is measurable.

## Design Tradeoffs

- JSONB is used for raw payloads and flexible evidence fields so source payload changes do not force migrations every week.
- Critical query fields stay relational and indexed instead of being buried in JSONB.
- `stocks` is retained as the user-facing table name, but it behaves as an underlying instrument master.
- Native PostgreSQL enum types are avoided for now; check-constrained string enums are easier to evolve during early product discovery.

