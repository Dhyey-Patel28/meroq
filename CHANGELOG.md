# Changelog

## 1.0.0 - Exportable insight reports

### Added
- Added a dedicated Report tab for the current run.
- Added downloadable Markdown reports summarizing prediction, sentiment, risk simulation, watchlist highlights, and model comparison results.
- Added optional watchlist CSV export from the Report tab.
- Added `src/reporting.py` to keep report generation separate from the Streamlit UI.

### Changed
- Replaced the static News Sentiment intro copy with a dynamic summary of the actual headlines, sentiment score, confidence, selected engine, and source used.
- Updated the dashboard-ready message to include the new Report tab.

### Notes
- Reports are generated locally and do not include API keys or local cache databases.


## 0.9.0 — Watchlist intelligence dashboard

### Added

- Watchlist tab for scanning a configurable universe of tickers.
- `src/watchlist.py` for multi-ticker signal, sentiment, risk, and ranking logic.
- `scripts/scan_watchlist.py` for command-line watchlist scans.
- Watchlist sidebar controls for ticker universe, max tickers, sentiment, and risk toggles.
- Meroq Score, a transparent 0–100 ranking score combining model probability, sentiment, trend, and downside-risk estimates.
- Watchlist ranking table, score bar chart, probability-vs-risk scatter chart, and quick-read summary.
- `docs/WATCHLIST_INTELLIGENCE.md` and `notebooks/07_watchlist_intelligence.ipynb`.

### Changed

- Production roadmap now points toward exportable reports, portfolio-level risk views, and scheduled refresh workflows.

## 0.8.2 — Product UX polish

### Changed

- Collapsed advanced sidebar controls into focused sections so the default screen is less cluttered.
- Reset default widget keys so Fast mode starts with XGBoost and practical settings instead of previously persisted heavy settings.
- Simplified the Prediction tab to show the final signal, probability, sentiment overlay, and market snapshot first.
- Moved the simple split diagnostic chart behind an expander.
- Moved sentiment modeling readiness details and raw sentiment feature previews behind expanders.
- Updated the roadmap copy to reflect a product-polish release.

## 0.8.1

- Fixed duplicate Streamlit chart keys when the prediction panel re-renders after sentiment fusion.
- Fixed `scripts/refresh_sentiment_features.py` so it can be run directly from the project root.
- Improved sentiment modeling readiness by combining persisted daily sentiment features with the current run.
- Added daily sentiment feature inventory to `scripts/inspect_data_store.py`.


## 0.8.0 — Sentiment feature store and modeling readiness

### Added

- Sentiment Modeling tab for feature readiness and experimental modeling comparison.
- `src/sentiment_modeling.py` for lagged sentiment feature joins and technical vs. sentiment-enhanced simple-split tests.
- Daily sentiment feature persistence in the local news database.
- Sentiment feature inventory in the Data Manager.
- `scripts/refresh_sentiment_features.py` for watchlist-level sentiment feature refreshes.
- `docs/SENTIMENT_MODELING.md` and `notebooks/06_sentiment_aware_modeling.ipynb`.

### Changed

- Roadmap now separates latest-news signal fusion from historical sentiment-aware modeling.
- Daily sentiment features are saved when News Sentiment runs, making repeated research runs easier to inspect.

## 0.7.0 — Sentiment-aware signal fusion

### Added

- Conservative sentiment-aware probability overlay for the main prediction.
- Signal fusion controls in the sidebar.
- Prediction tab cards comparing base probability, sentiment adjustment, and adjusted probability.
- Daily sentiment feature aggregation for future historical sentiment modeling.
- `src/signal_fusion.py` and `src/sentiment_features.py`.
- Documentation for the signal-fusion layer.

### Changed

- News sentiment output now includes daily sentiment feature rows.
- Top metrics now distinguish base model probability from sentiment-aware probability.

## 0.6.1 — Unified dependency setup

### Changed

- Consolidated app, NLP, and research dependencies into a single `requirements.txt`.
- Removed separate NLP/research requirements files.
- Updated app/help text and setup docs to use one install command.

## 0.6.0 — Local data layer and freshness controls

### Added

- Local market-data inventory table with ticker, interval, row count, date range, and refresh timestamp.
- Local news cache in `data/news_cache.sqlite`.
- Data Manager views for database files, market data inventory, and news cache inventory.
- News source option for all configured sources.
- News lookback, cache, and force-refresh controls in the sidebar.
- Refresh and inspection scripts:
  - `scripts/refresh_data.py`
  - `scripts/inspect_data_store.py`
  - `scripts/news_smoke_test.py`
  - `scripts/download_hf_models.py`
- `src/storage.py` for SQLite metadata, news cache, and local data inspection.

### Changed

- Price downloads now record metadata after saving to SQLite.
- News fetching can reuse local cache to reduce repeated API calls.
- Production roadmap now emphasizes local data contracts before scheduled jobs or hosted infrastructure.

## 0.5.2 — Public project polish and sentiment research structure

### Added

- Product-style documentation.
- Optional NLP and research requirements files.
- Research notebooks for price features, news sentiment, model comparison, and risk simulation.
- `.env.example` and `.gitattributes`.

### Changed

- Removed prototype-stage planning docs from the public-facing repo structure.

## 0.5.1 — Free finance sentiment ensemble

### Added

- Local Hugging Face finance sentiment model options:
  - `ProsusAI/finbert`
  - `yiyanghkust/finbert-tone`
  - `mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis`
- Ensemble sentiment mode.
- Lightweight financial lexicon fallback.
- Optional Finnhub and NewsAPI integrations.

## 0.5.0 — News sentiment foundation

### Added

- News Sentiment tab.
- Recent ticker headline fetching.
- Sentiment summary cards and charts.

## 0.4.0 — Monte Carlo risk simulation

### Added

- Risk Simulation tab.
- Simulated price paths.
- Return distribution and downside probability metrics.

## 0.3.0 — Advanced model comparison

### Added

- Multi-model comparison.
- Additional tree/boosting/ensemble models.
- Two-tab UX with Results and Run Details.

## 0.2.0 — Walk-forward backtesting

### Added

- Walk-forward validation.
- Equity curves.
- Trading metrics with transaction costs.

## 0.1.0 — Starter dashboard

### Added

- Streamlit app.
- yfinance data download.
- Technical indicators.
- XGBoost baseline prediction.
