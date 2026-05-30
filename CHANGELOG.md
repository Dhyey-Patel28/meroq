# Changelog

## 1.3.0 — Service layer extraction

### Added

- Added `src/services.py` with a reusable `SingleTickerAnalysisRequest` and `run_single_ticker_analysis()` entry point.
- Added `scripts/analyze_ticker.py` so the core single-ticker analysis can run without Streamlit.
- Added `docs/SERVICE_LAYER.md` documenting the service contract and future FastAPI/Next.js migration path.
- Added `notebooks/09_service_layer_research.ipynb` as a lightweight research notebook for using the service layer.

### Changed

- Clarified the README around command-line usage and the Streamlit-to-service separation.

## 1.2.1 — Senior QA polish and predictable analysis modes

### Fixed

- Analysis modes now enforce their preset model, comparison, and walk-forward settings unless Custom mode is selected.
- Prevented stale Streamlit widget state from leaving Fast or Full mode with an old manually selected model such as Stacking Ensemble.
- Collapsed Markdown report preview by default so the Report tab is less overwhelming.
- Added a warning when the Hugging Face sentiment ensemble is combined with many headlines because that run can be slow on local CPU.
- Kept generated SQLite databases and Python cache files out of the release package.

### Changed

- Simplified the initial waiting state with a recommended workflow for first-time users.
- Moved manual model/backtest controls behind Custom mode to make the default experience more predictable.
- Added `docs/QA_AUDIT.md` with user-impact findings, severity, and remediation notes.

## 1.2.0 — Portfolio risk and exposure view

### Added

- Added a Portfolio results tab that turns a watchlist scan into weighted exposure.
- Added equal-weight and custom-weight portfolio controls.
- Added portfolio-level metrics: weighted up probability, Meroq Score, downside exposure, positive-sentiment exposure, high-risk weight, and weighted daily return.
- Added portfolio weight and weighted downside contribution charts.
- Added `src/portfolio.py` and `scripts/analyze_portfolio.py`.
- Added `docs/PORTFOLIO_RISK.md` and `notebooks/08_portfolio_risk_research.ipynb`.

### Fixed

- Kept report and CSV download buttons from rerunning the app by using Streamlit's ignored download click behavior.

## 1.1.0 — Deployment readiness and cleaner product UI

### Changed

- Removed the internal Production Roadmap tab from the main Results interface.
- Kept roadmap/deployment guidance in documentation instead of product tabs.
- Added deployment guidance for local use, hosted demos, and secrets handling.
- Added a frontend migration plan for a future FastAPI + Next.js architecture.
- Added an example Streamlit secrets file for hosted environments.
- Updated README to explain the current Streamlit-first direction and future migration path.

## 1.0.1 — Company-aware news matching

### Fixed

- Replaced raw-ticker NewsAPI search with company-name-first search.
- Added ticker-to-company resolution through yfinance profile metadata.
- Added company alias generation for names such as Dave & Buster's / Dave Busters.
- Added relevance filtering so broad NewsAPI results like sports, entertainment, or generic uses of ambiguous tickers are removed before sentiment scoring.
- Filtered local cached headlines through the same relevance layer before reuse.
- Added News Sentiment UI details showing resolved company name, aliases, and the NewsAPI query used.

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
