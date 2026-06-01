# Meroq

> Release 1.9.6 upgrades the ticker page into an analyst one-pager with stance, conviction, primary driver, evidence quality, watch items, and research checks.


Current release: 1.9.6 — Ticker analyst brief.

Meroq is a local market-intelligence project for stock movement research. It combines price features, machine-learning signals, news sentiment, Monte Carlo risk simulation, watchlist scanning, portfolio exposure views, a Streamlit dashboard, a FastAPI backend, and a growing Next.js frontend.

> Educational/research use only. Meroq is not financial advice and should not be treated as an automated trading system.

## Current release

**1.9.6 — Ticker analyst brief**

Meroq now builds a local analyst-style brief for each ticker analysis. The ticker page surfaces stance, conviction, primary driver, evidence quality, key points, watch items, and research checks before the raw model/risk/news detail.

## Main capabilities

- Single-ticker prediction, analyst brief, and forecast-style summary
- Technical indicators and XGBoost-based directional modeling
- Model comparison and walk-forward backtesting
- Monte Carlo risk simulation
- Company-aware news fetching and target-aware sentiment analysis
- Sentiment gold benchmark and evaluation CLI
- Sentiment-aware signal overlay
- Meroq Grade and component rating labels
- Watchlist screener with Meroq Score, bucket labels, research priority, and scan notes
- Ticker analyst brief with stance, conviction, primary driver, watch items, and research checks
- Watchlist presets, input cleanup, progressive scan controls, and queue filters
- Portfolio command center with exposure, concentration, grade distribution, driver analysis, and scenario lab
- Markdown/CSV reporting
- FastAPI backend for reusable analysis endpoints
- Next.js frontend client for the API
- Lightweight pytest suite and GitHub Actions CI

## Project layout

```text
meroq/
├── app.py                     # Streamlit dashboard
├── api/                       # FastAPI backend
├── frontend/                  # Next.js frontend client
├── src/                       # Core analysis modules
├── scripts/                   # CLI utilities and smoke tests
├── tests/                     # Lightweight automated tests
├── docs/                      # Architecture, API, testing, frontend docs
├── notebooks/                 # Research notebooks
├── data/                      # Local generated data, ignored except .gitkeep
└── requirements.txt
```

## Setup

Create and activate a Python environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a local environment file for optional API keys:

```powershell
Copy-Item .\.env.example .\.env
```

Do not commit `.env`.

## Run Streamlit

```powershell
python -m streamlit run app.py
```

Open:

```text
http://localhost:8501
```

## Run the FastAPI backend

```powershell
python scripts/run_api.py --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Run the Next.js frontend

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

The frontend calls the API at `http://127.0.0.1:8000` by default. You can override this with `NEXT_PUBLIC_MEROQ_API_URL` in a local frontend env file.

## Run tests

```powershell
python scripts/run_tests.py
```

The default test suite avoids live market/news/model downloads so it can run in CI.

## Useful CLI commands

Single-ticker analysis:

```powershell
python scripts/analyze_ticker.py --ticker AAPL --period 5y --interval 1d
```

Watchlist scan:

```powershell
python scripts/scan_watchlist.py --tickers AAPL,MSFT,NVDA,SPY --period 5y --interval 1d
```

Portfolio analysis:

```powershell
python scripts/analyze_portfolio.py --tickers AAPL,MSFT,NVDA,SPY --weights "AAPL:30,MSFT:25,NVDA:25,SPY:20"
```

Inspect local data store:

```powershell
python scripts/inspect_data_store.py
```

## Optional news and NLP configuration

Meroq works without paid APIs. Optional keys may be added to `.env`:

```env
FINNHUB_API_KEY=
NEWSAPI_API_KEY=
```

NewsAPI's free Developer plan should only be used for local development/testing with your own key. Do not commit keys or use your personal key for a public hosted app.

Hugging Face finance sentiment models run locally after download; no Hugging Face API key is required for the default local workflow.

## Notes on generated files

The repository should not commit:

- `.env`
- `.venv/`
- `data/*.sqlite`
- `data/*.db`
- `__pycache__/`
- `*.pyc`
- `*.zip`
- `frontend/.next/`
- `frontend/node_modules/`

These are ignored by `.gitignore`.


## 1.8.1 UX update

- Frontend ticker analysis now shows source-linked headline cards.
- News links open in a new tab so users can inspect the original source.
- The frontend copy is more human-centered: signal first, evidence second, raw tables behind disclosure.

## 1.8.4 frontend update

- The Next.js ticker page keeps the forecast-range visualization: current close, median simulated path, and 10th/90th percentile range.
- Metric cards now use small hover/focus info icons instead of always-visible explanatory text.
- Suggested ticker chips make the ticker workflow easier to try without typing.
- CSS alignment values were updated for better browser compatibility and to remove the Autoprefixer warning.
- The frontend package keeps the PostCSS npm override to avoid the audit issue without downgrading Next.js.
- D3 remains on the roadmap; this release keeps the chart lightweight while the API contract stabilizes.

## Sentiment evaluation

Evaluate the local target-aware sentiment benchmark:

```powershell
python scripts/evaluate_sentiment.py --engine lightweight
```

Use regression gates before changing sentiment rules:

```powershell
python scripts/evaluate_sentiment.py --engine lightweight --fail-under-accuracy 0.90 --fail-under-cautionary-recall 0.90
```
