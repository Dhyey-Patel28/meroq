# Meroq

**Meroq** is a local-first market intelligence dashboard for stock movement analysis, model comparison, walk-forward backtesting, Monte Carlo risk simulation, and recent-news sentiment analysis.

It is built for research and education. It is **not financial advice**.

## Current release

**0.7.0 — Sentiment-aware signal fusion**

This release adds a transparent signal-fusion layer that combines the base ML prediction with recent-news sentiment:

- Local SQLite market-data inventory with refresh metadata
- Local SQLite news cache to reduce repeated API calls
- Multi-source news aggregation with yfinance, Finnhub, and optional NewsAPI
- Local Hugging Face finance sentiment engines installed through a single `requirements.txt`
- Sentiment-aware signal overlay that keeps the base model probability visible
- Conservative probability adjustment from recent-news sentiment
- Daily sentiment feature aggregation for future historical sentiment modeling
- Scripts for data refresh, data-store inspection, news smoke tests, and model downloads

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
- Fetch recent company headlines
- Score headlines with lightweight or local Hugging Face financial sentiment models
- Combine model probability with recent-news sentiment as a transparent signal overlay
- Aggregate headline sentiment into daily feature rows
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
