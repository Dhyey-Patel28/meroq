# Testing and Quality Checks

Meroq includes a small automated test suite for the reusable service/API layer.
These tests are intentionally lightweight: they avoid long model training and
focus on deterministic logic, API metadata, and regression-prone code paths.

## Run tests

```bash
python scripts/run_tests.py
```

Or directly:

```bash
python -m pytest tests -q
```

## What is covered

- API health and metadata endpoints
- Root API endpoint
- Portfolio weight parsing
- Portfolio summary calculations
- A regression check for the API portfolio weight parser

## What is intentionally not covered yet

Full ticker analysis tests that call live data providers are not included in
the default test suite because they can be slow and depend on network/data-provider
availability. Use smoke-test scripts for those paths:

```bash
python scripts/analyze_ticker.py --ticker AAPL --period 5y --interval 1d
python scripts/api_smoke_test.py --ticker AAPL
python scripts/news_smoke_test.py --ticker AAPL --source all_configured --engine lightweight --force-refresh
```

## Recommended pre-commit checklist

```bash
python scripts/run_tests.py
python scripts/analyze_ticker.py --ticker AAPL --period 5y --interval 1d
python -m streamlit run app.py
```

Also confirm `.env` is not staged before committing.
