# Local Data Layer

Meroq 0.6.0 adds a more explicit local data layer.

## Market database

`data/market_data.sqlite` stores OHLCV tables such as:

- `prices_AAPL_1d`
- `prices_SPY_1wk`

It also stores `price_metadata`, which tracks:

- ticker
- interval
- requested period
- row count
- start date
- end date
- last refresh timestamp

## News cache

`data/news_cache.sqlite` stores cached headlines by ticker and source. This reduces repeated API calls and keeps sentiment development faster.

## Inspecting data

Run:

```powershell
python scripts/inspect_data_store.py
```

## Refreshing data

Run:

```powershell
python scripts/refresh_data.py --period max --interval 1d
```

Use `--force` to ignore freshness checks.
