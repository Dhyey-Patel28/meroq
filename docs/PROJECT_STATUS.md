# Project Status

## Current Stage

**Stage 4.2 — Stability, UX polish, documentation, and Git readiness**

## Working Features

- Stock price download
- SQLite local storage
- Technical indicator generation
- Primary model prediction
- Advanced model comparison
- Walk-forward backtesting
- Monte Carlo risk simulation
- Product-facing Results tab
- Operational Run Details tab
- Default 10-stock universe
- Bootstrap script for historical data
- Documentation for setup and Git workflow

## Known Limitations

- Predictions are experimental and noisy
- The app retrains models during each run
- The project still uses SQLite instead of PostgreSQL
- No scheduled data refresh yet
- No sentiment/news ingestion yet
- No model registry or persistent model artifacts yet
- No automated tests yet
- No API backend yet
- No React production frontend yet

## Recommended Next Stage

**Stage 5 — NLP Sentiment**

Goals:

- Fetch recent company news
- Run FinBERT sentiment
- Create sentiment features
- Add sentiment tab
- Compare models with and without sentiment features
- Store sentiment results locally

## What Not To Add Yet

Avoid Kafka and Spark for now.

They make sense later if Meroq handles:

- Live tick streams
- Many thousands of tickers
- Real-time news streams
- Multi-service event pipelines
- Heavy distributed data processing

For the current 10-stock universe, SQLite plus scheduled jobs is enough.
