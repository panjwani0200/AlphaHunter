# AlphaHunter Backend

FastAPI backend for data collection, scanning, scoring, alerting, CSV exports, and AI-assisted analysis.

Phase 2 adds the database model layer and Alembic baseline migration. Business logic still begins in later phases after the schema is approved.

## Module Boundaries

- `api`: HTTP and WebSocket boundaries
- `core`: settings and runtime configuration
- `db`: database session, migrations, repositories, and persistence models
- `collectors`: external data source adapters
- `scanners`: broad market filtering and candidate shortlisting
- `engine`: deterministic scoring and risk engines
- `ai`: natural-language reasoning over structured signals
- `alerts`: Telegram and notification delivery
- `scheduler`: recurring jobs during market hours
- `domain`: shared domain contracts
- `utils`: infrastructure helpers that do not own market logic

## Migrations

Run from this directory:

```powershell
alembic upgrade head
```
