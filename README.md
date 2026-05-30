# Meroq

**Meroq** is a local-first market intelligence dashboard for stock movement analysis, model comparison, walk-forward backtesting, Monte Carlo risk simulation, and recent-news sentiment analysis.

It is built for research and education. It is **not financial advice**.

## Current release

**1.2.0 — Portfolio risk and exposure view**

This release adds a portfolio-level risk view on top of the existing watchlist scan:

- Adds a Portfolio results tab
- Converts watchlist scan rows into equal-weight or custom-weight portfolio exposure
- Computes weighted signal probability, weighted sentiment, Meroq Score, downside-risk exposure, and high-risk allocation
- Adds portfolio weight and downside-contribution charts
- Adds a command-line portfolio analyzer and portfolio-risk documentation
- Keeps the Streamlit UI focused while preserving the FastAPI/Next.js migration plan in docs

## Core capabilities

- Download historical OHLCV data with `yfinance`
- Generate technical indicators including SMA, EMA, RSI, MACD, Bollinger Bands, ATR, volatility, and stochastic oscillator
- Train and compare multiple models:
  - Momentum baseline
  - Logistic regression
  - Random forest
  - Extra Trees
  - HistGradientBoosting
  - XGBoost
  - LightGBM
  - CatBoost
  - Soft voting ensemble
  - Stacking ensemble
- Predict next-period up/down probability
- Run walk-forward validation
- Simulate strategy behavior with transaction costs
- Run Monte Carlo price-risk simulation
- Scan a watchlist and rank symbols with a transparent Meroq Score
- Analyze a scanned watchlist as a weighted portfolio with exposure and downside-risk summaries
- Resolve tickers to company names before broad news search
- Fetch and relevance-filter recent company headlines
- Score headlines with lightweight or local Hugging Face financial sentiment models
- Combine model probability with recent-news sentiment as a transparent signal overlay
- Aggregate headline sentiment into daily feature rows
- Persist daily sentiment features to the local data layer
- Compare technical-only and sentiment-enhanced model variants when coverage is sufficient
- Cache market/news data locally

## Installation

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The single `requirements.txt` includes the dashboard, modeling libraries, local Hugging Face sentiment stack, and research notebook dependencies.

## Run the app

```powershell
python -m streamlit run app.py
```

## Deployment and frontend direction

Meroq currently uses Streamlit because it is the fastest way to iterate on data science workflows, model diagnostics, and research UX. A React/Next.js frontend is a good future direction after the backend/API boundary is stable.

Read:

- `docs/DEPLOYMENT.md` for local/public-demo guidance and secrets handling
- `docs/FRONTEND_MIGRATION.md` for the Streamlit-to-FastAPI/Next.js migration plan
- `docs/PORTFOLIO_RISK.md` for the portfolio exposure view

## Optional API keys

Meroq can run without paid APIs. Optional news providers can be enabled with your own keys.

Create a local `.env` file:

```powershell
Copy-Item .\.env.example .\.env
notepad .env
```

Example:

```env
FINNHUB_API_KEY=your_finnhub_key
NEWSAPI_API_KEY=your_newsapi_key
```

Do not commit `.env`.

NewsAPI note: the free Developer plan is intended for local development/testing. Do not use a free NewsAPI key for a hosted, staging, or production deployment.

## Recommended first run

Use these settings first:

- Ticker: `AAPL`
- History period: `5y`
- Interval: `1d`
- Analysis mode: `Fast mode`
- News source: `All configured sources, recommended`
- Sentiment engine: `Lightweight financial lexicon`
- Run walk-forward comparison: off
- Use sentiment-aware signal overlay: on

After the basic run works, try:

- Sentiment engine: `ProsusAI/finbert`
- Sentiment engine: `Finance sentiment ensemble`

The first Hugging Face run may be slow because models are downloaded and cached locally.

## Local data scripts

Refresh default watchlist market data:

```powershell
python scripts/refresh_data.py --period max --interval 1d
```

Force refresh:

```powershell
python scripts/refresh_data.py --period max --interval 1d --force
```

Inspect local data inventory:

```powershell
python scripts/inspect_data_store.py
```

Test news + sentiment:

```powershell
python scripts/news_smoke_test.py --ticker AAPL --source all_configured --engine lightweight
```

Run a watchlist scan from the command line:

```powershell
python scripts/scan_watchlist.py --tickers AAPL,MSFT,NVDA,SPY --period 5y --interval 1d
```

Download Hugging Face models ahead of time:

```powershell
python scripts/download_hf_models.py
```

## Project layout

```text
meroq/
├── app.py
├── requirements.txt
├── scripts/
│   ├── bootstrap_watchlist.py
│   ├── refresh_data.py
│   ├── inspect_data_store.py
│   ├── news_smoke_test.py
│   ├── scan_watchlist.py
│   └── download_hf_models.py
├── src/
│   ├── backtesting.py
│   ├── charts.py
│   ├── config.py
│   ├── data_loader.py
│   ├── features.py
│   ├── model.py
│   ├── news_sentiment.py
│   ├── sentiment_features.py
│   ├── signal_fusion.py
│   ├── risk_simulation.py
│   ├── watchlist.py
│   └── storage.py
├── docs/
├── notebooks/
└── data/
```

## Data storage

Generated local files are ignored by Git:

- `data/market_data.sqlite`
- `data/news_cache.sqlite`
- `.env`
- `.venv/`
- Hugging Face model cache directories

## License

See `LICENSE`.


## Exportable Reports

Meroq includes a **Report** tab that generates a local Markdown report for the current analysis run. The report summarizes:

- latest model signal and probability
- sentiment-aware probability adjustment
- recent-news sentiment summary
- Monte Carlo risk simulation summary
- watchlist highlights
- model comparison snapshot
- interpretation notes and limitations

Reports are generated locally in the browser session. They do not include API keys, `.env` values, SQLite databases, or local cache files.

