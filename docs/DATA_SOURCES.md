# Data Sources

## Price data

Meroq uses `yfinance` for OHLCV history. This is appropriate for research and education but not guaranteed for production-grade trading systems.

## News data

Meroq supports:

- yfinance news: no API key.
- Finnhub: optional user-provided free key.
- NewsAPI: optional user-provided developer key.

The recommended app setting is **All configured sources**. It combines no-key yfinance headlines with any optional local keys present in `.env`.

## API key policy

Meroq does not provide, store, sell, or proxy API keys. Users must bring their own keys and follow provider terms. Real keys belong in `.env`, which is ignored by Git.

## Local cache

Market data is stored in `data/market_data.sqlite`.
News data is stored in `data/news_cache.sqlite`.

Both generated database files are ignored by Git.


## Company-aware NewsAPI search

Raw ticker search is not reliable for ambiguous tickers such as `PLAY`, `ON`, `GO`, or `NOW`. Meroq resolves the ticker into a company name and searches NewsAPI with company aliases plus financial context terms. Returned rows are relevance-scored and filtered before sentiment scoring.
