# Changelog

## Stage 4.2 — Stability, UX Polish, Documentation, and Git Readiness

This is the checkpoint before NLP sentiment.

### Added

- Analysis mode selector:
  - Fast mode
  - Research mode
  - Full analysis mode
  - Custom
- Safer defaults for development:
  - XGBoost primary model
  - Core fast model comparison
  - Monte Carlo risk simulation on
  - Slow walk-forward loops off by default
- Risk-adjusted outlook in top metrics
- Plain-English Monte Carlo interpretation in the Risk Simulation tab
- Documentation folder:
  - `docs/USAGE.md`
  - `docs/PROJECT_STATUS.md`
  - `docs/GIT_WORKFLOW.md`
  - `docs/STAGE_5_NLP_PLAN.md`
- `.streamlit/config.toml` to disable Streamlit usage stats prompt

### Fixed

- Duplicate `st.plotly_chart` key issues
- Deprecated `use_container_width=True` warnings by using `width="stretch"`
- Persisted widget defaults from older versions by giving important sidebar widgets new Stage 4.2 keys

### Changed

- Production Roadmap now reflects Stage 4.2 status
- Default experience is faster and safer
- Full analysis mode is still available but intentionally marked as slower

---

## Stage 4.1 — Bugfix

### Fixed

- Duplicate Plotly chart keys during repeated model comparison rendering
- Cleaned chart render keys for simple and final comparison states

---

## Stage 4 — Monte Carlo Risk Simulation

### Added

- Risk Simulation tab
- Monte Carlo simulated price paths
- Percentile price range chart
- Final return distribution chart
- Probability of positive return
- Probability of loss greater than 5%
- Probability of gain greater than 5%
- Expected max drawdown
- Drift assumptions:
  - Historical mean
  - Recent mean
  - Zero drift
  - Model-adjusted

---

## Stage 3.7 — Two-Tab UX

### Added

- Top-level `Results` tab for product output
- Top-level `Run Details` tab for pipeline status
- Clean result tabs that populate as data becomes available

---

## Stage 3.6 — Run Monitor

### Added

- Progress bar
- Stage status table
- Run event log
- Insights generated during the pipeline
- Model and fold progress callbacks

---

## Stage 3.5 — Advanced Model Suite

### Added

- Extra Trees
- HistGradientBoosting
- LightGBM
- CatBoost
- Soft Voting Ensemble
- Stacking Ensemble
- Model dependency availability table

---

## Stage 3 — Model Comparison

### Added

- Momentum baseline
- Logistic regression
- Random forest
- XGBoost
- Simple chronological split comparison
- Optional walk-forward model comparison

---

## Stage 2 — Walk-Forward Backtesting

### Added

- Walk-forward validation
- Equity curves
- Long-only strategy simulation
- Long/short strategy simulation
- Sharpe ratio
- Max drawdown
- Win rate
- Transaction cost setting

---

## Stage 1 — Starter Dashboard

### Added

- Streamlit dashboard
- yfinance data download
- Technical indicators
- XGBoost prediction
- Plotly charts
- SQLite local storage
