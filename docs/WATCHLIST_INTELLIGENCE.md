# Watchlist Intelligence

Meroq's watchlist view is designed to answer a practical research question:

> Across a small universe, which symbols deserve attention today?

It is not a trading system and it should not be treated as financial advice. The watchlist scan is a ranking and triage layer built on top of the same components used by the single-ticker dashboard.

## What the scan runs

For each symbol, Meroq runs a fast local pipeline:

1. Download or refresh historical OHLCV data.
2. Build technical indicators and model features.
3. Train a lightweight XGBoost classifier.
4. Predict next-period up probability.
5. Optionally fetch recent headlines and score sentiment.
6. Optionally run a lightweight Monte Carlo risk simulation.
7. Combine the outputs into a transparent 0–100 Meroq Score.
8. Add a screener bucket, research-priority score, evidence count, and scan note for triage.

## Meroq Score

The Meroq Score is a product-ranking score, not a prediction target. It combines:

- final up probability
- recent-news sentiment score
- model-adjusted risk simulation probability
- probability of losing more than 5 percent over the simulation horizon
- short-term trend context from technical indicators

The exact scoring formula is intentionally simple and visible in `src/watchlist.py`. It should be tuned only after more backtesting and live-observation logs are available.

## Recommended settings

For responsive local use:

- use 5 to 10 tickers
- use `5y` or `10y` daily data
- keep sentiment on lightweight mode for broad scans
- use Hugging Face sentiment models for single-ticker deep dives
- keep risk simulation at 500 paths for watchlist scans

## Limitations

The watchlist scan is still local and sequential. It is intentionally conservative to keep the project easy to understand. If the app later needs to scan hundreds of tickers, the next step is a scheduled data-refresh layer and a database-backed batch pipeline, not a bigger Streamlit loop.


## Screener buckets

Release 1.9.5 adds queue labels so the watchlist behaves more like a practical screener:

- **Research queue** — stronger local score, grade, and up-probability setup.
- **Momentum watch** — constructive enough to monitor, but not the strongest candidate.
- **Risk review** — high downside risk, cautionary sentiment, weak grade, or low score needs inspection first.
- **Low priority** — usable data, but currently lower priority than stronger names.
- **Data issue** — provider/model could not produce a usable row for the symbol.

Each successful row also includes `research_priority`, `evidence_count`, and `scan_note`. These labels are meant to help decide what to inspect next. They are not recommendations to buy, sell, or rebalance.

## Command-center summary

The watchlist summary now exposes:

- top research candidates
- momentum-watch rows
- risk-review rows
- sentiment-watch rows
- data issues
- grade distribution
- scan alerts

The Next.js watchlist page uses those same concepts locally as rows stream in one ticker at a time.
