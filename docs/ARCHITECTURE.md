# Architecture

Meroq is a local-first Streamlit application.

## Runtime flow

1. User selects ticker and analysis settings.
2. Price data is downloaded or refreshed through `src/data_loader.py`.
3. Price data is saved to `data/market_data.sqlite`.
4. Feature engineering creates technical indicators.
5. The selected model is trained and evaluated.
6. Optional risk simulation estimates price outcome ranges.
7. Optional news sentiment fetches recent headlines, scores them, and caches them locally.
8. Results render in product tabs; operational progress renders in Run Details.

## Main modules

- `app.py` — Streamlit UI and orchestration.
- `src/data_loader.py` — OHLCV download and local saving.
- `src/storage.py` — SQLite metadata, freshness checks, and cache inspection.
- `src/features.py` — technical indicators and target construction.
- `src/model.py` — model training, prediction, and model comparison.
- `src/backtesting.py` — walk-forward validation and trading metrics.
- `src/risk_simulation.py` — Monte Carlo price simulation.
- `src/news_sentiment.py` — news fetching and financial sentiment scoring.
- `src/charts.py` — Plotly visualizations.

## Local-first design

Meroq avoids paid hosted inference by default. Price/news data and model caches are local. Optional API keys are read from `.env` and never committed.


## Sentiment-aware signal fusion

The current prediction stack has two layers:

1. **Base model layer** — technical indicators and price-derived features train a classifier that estimates next-period up probability.
2. **Signal fusion layer** — recent-news sentiment is converted into a capped probability adjustment and shown separately from the base model output.

This keeps the dashboard explainable while preparing the project for historical sentiment-aware training.


## Sentiment modeling layer

Release 0.8.0 adds a separate sentiment modeling layer. The recent-news signal overlay remains a transparent adjustment to the latest prediction, while `src/sentiment_modeling.py` joins lagged daily sentiment features to historical model rows for experimental model comparison. This separation keeps the dashboard honest about what is recent context and what is historically trained signal.
