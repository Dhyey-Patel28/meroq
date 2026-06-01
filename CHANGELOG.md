# Changelog

## 1.9.4 — Portfolio scenario lab

### Added
- Added current, equal-weight, and research-weighted portfolio scenario comparison fields to `POST /portfolio/analyze`.
- Added research-weight and research-weight-delta fields for holdings so users can see what the scenario would add or trim.
- Added scenario add/trim lists and allocation-review notes for portfolio triage.
- Added portfolio scenario lab cards to the Next.js portfolio page.
- Added regression coverage for scenario comparison output.

### Changed
- Polished portfolio chart layout so donut legends no longer crowd or overflow narrow command-center cards.
- Bumped API metadata to 1.9.4 and frontend package version to 0.3.9.

### Notes
- Scenario weights are transparent diagnostic what-if views. They are not allocation advice and do not require paid data.

## 1.9.3 — Portfolio command center

### Added
- Added portfolio concentration labels, largest-position metadata, and a portfolio health label.
- Added grade distribution, top Meroq score contributors, top downside contributors, weakest holdings, and highest-risk holding summaries to portfolio API output.
- Added portfolio command-center insight cards and contributor lists to the Next.js portfolio page.
- Added downside contribution share and exposure-note columns to holdings tables.
- Added regression coverage for portfolio command-center fields.

### Changed
- Updated the portfolio summary sentence to include allocation concentration and the largest holding.
- Updated frontend API types to accept nested API records and arrays in summary payloads.
- Bumped API metadata to 1.9.3.

### Notes
- This release keeps the app free/local-first by deriving portfolio intelligence from existing watchlist scan outputs and user-supplied weights.


## 1.9.2 — Sentiment evaluation harness

### Added
- Added a local gold-labeled sentiment benchmark for target-aware headline scoring.
- Added a sentiment evaluation module and CLI that reports accuracy, macro-F1, relevance quality, cautionary recall, and latency.
- Added regression tests so tricky headlines such as PLAY risky/buy-instead cases remain cautionary.
- Added sentiment evaluation documentation.

### Changed
- Made `yfinance` import tolerant for lightweight offline sentiment evaluation/test paths.
- Tightened target relevance handling so non-financial alias collisions like Square dancers are not promoted to medium relevance.
- Bumped API metadata to 1.9.2.

### Notes
- This release is an accuracy-infrastructure release, not a UI release. It establishes a measurable path toward a Stockfish-like sentiment engine.

## 1.9.1 — Meroq Grades and component ratings

### Added
- Added a local Meroq Grade layer that converts Meroq Score into A-F research grades.
- Added component grades for momentum, risk, sentiment, model confidence, and data quality.
- Added grade badges to ticker, watchlist, portfolio, and ticker drill-down views.
- Added portfolio-grade summary fields and grade-aware portfolio holdings.
- Added regression tests for grade thresholds and cautionary grade summaries.

### Notes
- Grades are attention labels for research workflow. They are not buy/sell recommendations and do not require paid API data.

## 1.9.0 — Target-aware sentiment trust layer

### Added
- Added a target-aware sentiment correction layer that scores whether a headline is positive or cautionary for the selected ticker/company.
- Added headline-level relevance labels, target sentiment labels, reason tags, and plain-English sentiment explanations.
- Added regression tests for the PLAY risky/buy-instead failure case and low-relevance ambiguous headlines.

### Changed
- Sentiment summaries now use a display label such as Cautionary when negative headlines are target-specific warnings.
- Low-relevance and uncertain headlines are excluded from the ticker-level sentiment overlay when possible.
- Frontend news cards now show relevance, target-aware sentiment, reason tags, and explanation text.
- Bumped API metadata to 1.9.0 and frontend package version to 0.3.6.

### Notes
- This release does not add paid APIs or a slower LLM dependency. It improves trust with deterministic target-aware rules that run fast and remain testable.

## 1.8.8 — Watchlist presets and ticker hygiene

### Added
- Added built-in watchlist presets for core market, AI infrastructure, fintech/crypto beta, and consumer/autos.
- Added custom watchlist presets saved locally in the browser.
- Added input hygiene metrics for entered, unique, duplicate, queued, and max-limited tickers.
- Added clean-list and copy-clean-list actions before scanning.

### Changed
- Progressive scans now use the normalized unique ticker list, reducing wasted requests from duplicate or messy pasted input.
- Bumped frontend package version to 0.3.5.

### Notes
- Presets are stored only in local browser storage. They are not sent to the backend until the user runs a scan.

## 1.8.7 — Watchlist cleanup controls and table exports

### Added
- Added sortable table headers and CSV export support to frontend data tables.
- Added watchlist result filters for all, ready, issue, and high-risk rows.
- Added copy actions for ready and issue tickers so large scans are easier to clean up and rerun.
- Added portfolio holdings CSV export through the shared frontend table component.

### Changed
- Watchlist scan results now separate cleanup actions from the main ranked table, keeping the table focused on decision support.
- Bumped frontend package version to 0.3.4.

### Notes
- This release does not change model behavior or backend scoring. It improves frontend result management after long scans.

## 1.8.6 — Progressive watchlist UX and portfolio drill-down

### Added
- Added a one-ticker-at-a-time watchlist scan endpoint so the frontend can render rows progressively instead of waiting for the full universe.
- Added searchable, scrollable frontend tables with compact symbol legends and clickable rows.
- Added ticker detail modals with close-on-backdrop, Esc support, and source-linked news cards.
- Added portfolio donut charts for holding weights and signal posture.
- Added a root `template.tsx` reset boundary so page state resets cleanly when switching tabs.

### Changed
- Replaced raw failed-ticker errors with friendlier user-facing messages that explain the symbol may be delisted, renamed, unsupported, or temporarily unavailable.
- Bumped API metadata to 1.8.6 and frontend package version to 0.3.3.

### Notes
- This release keeps the existing source-link trust UX while making watchlist and portfolio workflows feel more like a product surface.
- D3.js visualizations remain a future enhancement after the current interaction patterns settle.

## 1.8.4 — Frontend HCD polish and CSS cleanup

### Added
- Added small hover/focus info icons to frontend metric cards so explanations are available on demand without cluttering the page.
- Added suggested ticker chips to the frontend ticker page for faster exploration.

### Changed
- Replaced CSS `align-items: start` with `flex-start` to resolve the Autoprefixer compatibility warning.
- Bumped API metadata to 1.8.4 and frontend package version to 0.3.2.

### Notes
- This is a polish release that keeps the 1.8.2/1.8.3 forecast UX and repository hygiene intact.
- D3 remains planned for a later visualization phase after the frontend data contracts settle.

## 1.8.3 — Repo Hygiene Recovery

- Restored `.gitignore`, `.gitattributes`, `.github/workflows/ci.yml`, and `data/.gitkeep` to the release package.
- Kept the 1.8.2 frontend forecast range UX and PostCSS dependency override.
- Added generated frontend build metadata (`frontend/tsconfig.tsbuildinfo`) to `.gitignore`.
- Ensured release packages do not require committing `.env`, `.venv`, SQLite databases, `.next`, `node_modules`, or cache files.


## 1.8.2 — Frontend forecast UX and dependency hardening

### Added
- Added a forecast-range visualization to the Next.js ticker page using the risk simulation percentiles returned by the API.
- Added a decision panel that summarizes direction, evidence, and risk in plain language before raw tables.
- Added `risk_percentiles` to the ticker analysis API details response.

### Changed
- Bumped API metadata to 1.8.2 and frontend package version to 0.3.1.
- Kept D3.js as a documented future visualization track; the current chart uses a lightweight accessible SVG component.
- Kept the PostCSS npm override in the frontend package to avoid the audit issue without using `npm audit fix --force`.

### Notes
- This release improves the frontend product experience without replacing the Streamlit research dashboard.

## 1.8.1 — Human-centered frontend and source-linked news

### Added
- Added source-linked news cards to the Next.js ticker page.
- Added `NewsCard` and `TrustPanel` frontend components.
- Added clickable URL rendering to the frontend data table.
- Added human-centered UX documentation and a D3 visualization roadmap.

### Changed
- Reworked the frontend dashboard and ticker page copy to focus on user decisions, evidence, and source inspection.
- Updated the Streamlit News Sentiment section with source article links.
- Updated API metadata to 1.8.1 and frontend package version to 0.3.0.

### Notes
- D3.js is documented as a future visualization track. It is not added as a runtime dependency yet, so this release remains lightweight.

## 1.8.0 — Frontend product client

### Added

- Upgraded the Next.js frontend from scaffold copy to functional product pages.
- Added API-backed ticker analysis, watchlist scan, and portfolio workflows in the frontend.
- Added frontend loading, error, probability, status, and metric components for a cleaner user experience.
- Added a frontend dashboard that explains the Streamlit/FastAPI/Next.js split.

### Changed

- Moved the frontend from a local `frontend.zip` artifact into a normal tracked `frontend/` directory.
- Removed generated frontend build output from the release package.
- Bumped FastAPI metadata version to 1.8.0.
- Updated frontend docs to describe the API-connected client.

### Notes

- Streamlit remains the complete primary UI.
- The Next.js app is now useful for local API testing and future UI migration work, but it is still not the full replacement for Streamlit.

## 1.7.0 — Frontend migration scaffold

### Added

- Added a separate `frontend/` Next.js + TypeScript scaffold.
- Added frontend pages for dashboard, ticker analysis, watchlist scan, and portfolio view.
- Added a typed frontend API client in `frontend/lib/api.ts`.
- Added reusable frontend components for metric cards, layout, backend status, and data tables.
- Added `docs/FRONTEND_SCAFFOLD.md` to document local frontend setup.

### Changed

- Bumped FastAPI metadata version to 1.7.0.
- Updated frontend migration documentation to reflect the new scaffold.
- Added frontend build artifacts and local env files to `.gitignore`.

### Notes

- Streamlit remains the primary UI.
- The Next.js app is an API-boundary proof of concept, not a full replacement yet.
- Frontend dependencies are managed inside `frontend/package.json`, separate from Python `requirements.txt`.

## 1.6.1 — API test-client cleanup

### Fixed

- Replaced `fastapi.testclient.TestClient` in API tests with direct `httpx.ASGITransport` and `httpx.AsyncClient` calls.
- Removed the Starlette/FastAPI TestClient deprecation warning without suppressing it.
- Kept API tests deterministic and local; no live market/news providers are called by the default test suite.

### Notes

- This change only affects tests. It does not change the Streamlit app, FastAPI endpoints, model logic, or local data layer.
- If the API later adds startup/shutdown lifespan behavior, tests may need a lifespan manager around the ASGI transport.


## 1.6.0 — GitHub Actions CI

### Added

- Added `.github/workflows/ci.yml` to run the lightweight pytest suite on pushes and pull requests to `main`.
- Added `docs/CI.md` to document the CI workflow, local equivalent commands, and secrets policy.

### Changed

- Updated testing documentation to distinguish deterministic CI tests from live-data smoke checks.
- Updated README to show the CI status badge and current release.

## 1.5.1 — API QA patch

### Fixed

- Fixed portfolio summary key mismatch that caused the new pytest suite to fail.
- Standardized portfolio summary output around `holding_count` and `weighted_meroq_score`.
- Kept `positions` and `portfolio_meroq_score` as compatibility aliases for existing UI/report code.
- Bumped API version metadata to 1.5.1.

## 1.5.0 - API hardening and automated QA

### Added
- Added `tests/` with lightweight pytest coverage for API and portfolio logic.
- Added `scripts/run_tests.py` for one-command local regression checks.
- Added `docs/TESTING.md` to document the automated and manual QA workflow.
- Added a root API endpoint (`GET /`) with links to health, metadata, and docs.
- Added configurable API CORS origins through `MEROQ_API_ALLOWED_ORIGINS`.

### Fixed
- Fixed the portfolio API endpoint to pass tickers and weights to `parse_portfolio_weights()` in the correct order.
- Added `*.zip` to `.gitignore` so local release packages are not accidentally committed.

### Changed
- Updated API documentation to reflect the current local backend workflow.
- Added pytest and httpx to the unified requirements file.

## 1.4.1 - Forecast-first Prediction UX

### Changed
- Redesigned the Prediction tab around a user-facing price forecast instead of a noisy historical probability diagnostic.
- Added a historical close + future forecast range chart using Monte Carlo percentiles.
- Added plain-English forecast copy with current close, median forecast, likely range, confidence, and reasoning.
- Translated RSI, MACD, and volatility into beginner-friendly momentum/trend/risk labels.
- Moved the simple split probability chart into an Advanced diagnostics expander.

### Added
- Added `make_price_forecast_chart()` for displaying historical close price plus expected future range.
- Added forecast UX documentation in `docs/FORECAST_UX.md`.


## 1.4.0 - API Backend Foundation

### Added
- Added a local FastAPI application under `api/main.py`.
- Added health, metadata, single-ticker analysis, watchlist scan, and portfolio analysis endpoints.
- Added `scripts/run_api.py` for launching the API.
- Added `scripts/api_smoke_test.py` for local API regression checks.
- Added `docs/API.md` and `notebooks/10_api_service_foundation.ipynb`.

### Changed
- Added FastAPI and explicit Uvicorn dependencies to the unified `requirements.txt`.
- Kept Streamlit as the primary UI while making Meroq easier to migrate to a future Next.js frontend.


## 1.3.1 — Streamlit dataframe rendering stability

### Fixed

- Added a dataframe rendering guard for mixed object columns before Streamlit serializes tables through Arrow.
- Prevented noisy PyArrow tracebacks from sidebar summary tables and diagnostic tables with mixed string/numeric values.
- Kept the 1.3.0 service layer unchanged.

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
