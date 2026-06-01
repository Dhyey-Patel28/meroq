# Meroq API

Meroq includes a local FastAPI backend so the analysis engine can be reused by
scripts, notebooks, and eventually a separate frontend.

## Run the API

```bash
python scripts/run_api.py --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```

## Main endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | API landing metadata |
| GET | `/health` | Health check |
| GET | `/metadata` | Models, news sources, sentiment engines, and defaults |
| GET | `/analysis/ticker/{ticker}` | Lightweight ticker analysis through query params |
| POST | `/analysis/ticker` | Configurable single-ticker analysis |
| POST | `/watchlist/scan` | Watchlist intelligence scan |
| POST | `/portfolio/analyze` | Portfolio view built from a watchlist scan |

## CORS

By default, the API allows local Streamlit and local Next.js development URLs:

```text
http://localhost:8501
http://127.0.0.1:8501
http://localhost:3000
http://127.0.0.1:3000
```

You can override this with an environment variable:

```env
MEROQ_API_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

## API smoke test

Start the API in one terminal:

```bash
python scripts/run_api.py --reload
```

Then run this in another terminal:

```bash
python scripts/api_smoke_test.py --ticker AAPL
```

## Automated tests

```bash
python scripts/run_tests.py
```

The test suite focuses on deterministic API and portfolio logic. Full live
data-provider workflows are handled through smoke-test scripts because they
can be slower and network-dependent.


## Frontend scaffold

Release 1.7.0 adds a small Next.js app under `frontend/` that calls these API endpoints during local development.

Start the API:

```bash
python scripts/run_api.py --reload
```

Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

The API CORS defaults already allow `http://localhost:3000` and `http://127.0.0.1:3000`.

## Ticker details: forecast percentiles

When `return_details=true`, `POST /analysis/ticker` includes `details.risk_percentiles` if risk simulation is enabled. The frontend uses these rows to render the forecast range:

- `p10`: downside range,
- `p50`: median path,
- `p90`: upside range.

This is a visualization aid, not a guaranteed price forecast.


## Watchlist progressive scan

### `POST /watchlist/scan-one`

Scans one ticker at a time for progressive frontend loading. It always returns a `row` object. Successful rows contain the normal watchlist fields. Failed rows return `status: failed` and a user-facing `error` message so the frontend can keep scanning other symbols.


## Meroq grade fields

Ticker, watchlist, and portfolio responses may include grade fields such as `meroq_grade`, `meroq_grade_label`, `momentum_grade`, `risk_grade`, `sentiment_grade`, `model_confidence_grade`, and `data_quality_grade`. These are local research labels for scanning and triage, not buy/sell recommendations.


## Portfolio command-center fields

Release 1.9.3 expands `POST /portfolio/analyze` with nested summary fields for production-style portfolio triage:

- `largest_position_ticker` and `largest_position_weight`
- `concentration_score` and `concentration_label`
- `portfolio_health_label`
- `grade_distribution`
- `top_score_contributors`
- `top_risk_contributors`
- `weakest_holdings`
- `highest_risk_holdings`
- `portfolio_alerts`

Holdings also include `score_contribution_share`, `downside_contribution_share`, and `exposure_note` when the required source fields are available.
