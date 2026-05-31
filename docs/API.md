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
