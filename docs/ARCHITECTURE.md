# Architecture

Meroq is currently a local Streamlit application with modular Python source files.

## Runtime flow

1. User selects ticker and analysis settings.
2. Price data is downloaded and saved to local SQLite.
3. Technical features are generated.
4. A primary model is trained and used for latest-period prediction.
5. Optional Monte Carlo simulation creates a risk range.
6. Optional news aggregation fetches recent headlines.
7. Optional sentiment models score headline tone.
8. Model comparison and walk-forward evaluation run when enabled.
9. Results render in product tabs; execution status renders in Run Details.

## Main modules

- `src/data_loader.py` — price download and local persistence
- `src/features.py` — technical indicators and targets
- `src/model.py` — model training, prediction, and comparison
- `src/backtesting.py` — walk-forward validation and strategy metrics
- `src/risk_simulation.py` — Monte Carlo price-path simulation
- `src/news_sentiment.py` — news fetch, cache, and sentiment scoring
- `src/charts.py` — Plotly chart builders
