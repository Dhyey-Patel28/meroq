# Meroq API Layer

Release 1.4.0 adds a local FastAPI backend that exposes the reusable analysis service created in the service-layer release.

The Streamlit app remains the main UI. The API is a bridge toward a future architecture where a Next.js frontend can call a Python backend.

## Why this exists

Meroq now has reusable services for ticker analysis, watchlist scanning, portfolio risk, news sentiment, and risk simulation. A local API makes those services accessible from:

- CLI tools
- notebooks
- integration tests
- a future Next.js frontend
- other local applications

## Run the API

From the project root:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/run_api.py --reload
```

Or directly:

```powershell
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/docs
```

FastAPI will show interactive API documentation.

## Smoke test

In a second terminal:

```powershell
python scripts/api_smoke_test.py --ticker AAPL
```

For a faster health-only test:

```powershell
python scripts/api_smoke_test.py --skip-analysis
```

## Endpoints

### `GET /health`

Returns service status and version.

### `GET /metadata`

Returns available models, model dependency status, news providers, sentiment engines, and default universe settings.

### `POST /analysis/ticker`

Runs a single-ticker analysis.

Example body:

```json
{
  "ticker": "AAPL",
  "period": "5y",
  "interval": "1d",
  "model_name": "xgboost",
  "include_risk": true,
  "include_news": true,
  "news_source": "all_configured",
  "sentiment_engine": "lightweight",
  "return_details": false
}
```

### `GET /analysis/ticker/{ticker}`

Convenience GET endpoint for simple requests.

Example:

```text
http://127.0.0.1:8000/analysis/ticker/AAPL?period=5y&interval=1d&model_name=xgboost
```

### `POST /watchlist/scan`

Runs a fast watchlist scan and returns ranked rows.

Example body:

```json
{
  "tickers": ["AAPL", "MSFT", "NVDA", "SPY"],
  "period": "5y",
  "interval": "1d",
  "include_sentiment": true,
  "include_risk": true
}
```

### `POST /portfolio/analyze`

Runs a watchlist scan and converts it into portfolio exposure metrics.

Example body:

```json
{
  "tickers": ["AAPL", "MSFT", "NVDA", "SPY"],
  "weights": "AAPL:30,MSFT:25,NVDA:25,SPY:20",
  "period": "5y",
  "interval": "1d"
}
```

## Free/API-key behavior

The API uses the same rules as the Streamlit app:

- `.env` is local only and must not be committed.
- yfinance news does not require an API key.
- Finnhub and NewsAPI are optional and read from local environment variables.
- Hugging Face models run locally after download.

## CORS

The API allows local development origins:

- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `http://localhost:8501`
- `http://127.0.0.1:8501`

This is enough for local Streamlit and a future Next.js frontend.

## Current limitations

The API is intentionally local-first. It is not yet a hardened public web service.

Before public deployment, add:

- authentication if needed
- rate limiting
- request timeouts/background jobs for slow models
- structured logging
- model/data cache controls
- deployment-specific secret management
