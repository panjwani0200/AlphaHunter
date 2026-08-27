# Data Source Strategy

## V1 Free Sources

- NSE India for official market, derivatives, options, and report data
- TradingView-compatible OHLC source where available
- yfinance as a fallback for non-critical OHLC gaps

## Reliability Requirements

Collectors should support:

- Browser-like headers
- Session persistence
- Retries with backoff
- Rate limiting
- Local caching
- Failure recovery
- Source-level observability

## Upgrade Path

Provider adapters should allow later migration to:

- Zerodha
- TrueData
- Opstra
- Broker APIs

The rest of the platform should depend on normalized internal contracts, not provider-specific payloads.

