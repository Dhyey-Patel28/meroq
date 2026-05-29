# Data sources

Meroq is designed to run locally without paid data dependencies.

## Price data

The app uses `yfinance` for historical OHLCV research data. Data is cached locally in `data/market_data.sqlite`.

## News data

Supported sources:

| Source | Key required | Usage in Meroq |
|---|---:|---|
| yfinance news | No | Default no-key fallback |
| Finnhub company news | Yes | Optional user key from `.env` |
| NewsAPI | Yes | Optional local development/testing provider |

## API key handling

- Keys are read from `.env`.
- `.env` is ignored by Git.
- Keys are not stored in source files.
- News results can be cached locally in `data/news_cache.sqlite` to reduce repeated requests.

## NewsAPI note

NewsAPI support is included for local development/testing with a user-provided key. Do not use a free NewsAPI Developer key in a hosted production deployment unless your NewsAPI plan permits that use.
