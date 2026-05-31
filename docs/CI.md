# Continuous Integration

Meroq uses GitHub Actions to run the lightweight automated test suite on every push and pull request to `main`.

## Workflow

The workflow lives at:

```text
.github/workflows/ci.yml
```

It runs:

```bash
python -m pip install -r requirements.txt
python scripts/run_tests.py
```

## What CI checks

The CI suite is intentionally focused on deterministic checks:

- API health and metadata routes
- API root route
- Portfolio weight parsing
- Portfolio summary calculations
- Regression coverage for the portfolio API parser

It does **not** run live ticker analysis, Streamlit, Hugging Face inference, or external news/API requests. Those flows depend on network availability, API keys, market-data providers, and local hardware. They should be tested with smoke scripts during local development.

## Local equivalent

Before pushing, run:

```bash
python scripts/run_tests.py
```

Useful manual smoke checks:

```bash
python scripts/analyze_ticker.py --ticker AAPL --period 5y --interval 1d
python scripts/api_smoke_test.py --ticker AAPL
python scripts/news_smoke_test.py --ticker AAPL --source all_configured --engine lightweight --force-refresh
```

## Secrets policy

CI does not require secrets. Optional news-provider keys should stay local in `.env` or in deployment-specific secret stores.

Never commit `.env`, API keys, local SQLite databases, model caches, or generated zip packages.
