# Meroq

**Meroq** is a predictive market intelligence dashboard for stock movement analysis, technical indicators, machine learning model comparison, walk-forward backtesting, and Monte Carlo risk simulation.

Current version: **Stage 4.2 — Stability, UX polish, documentation, and Git readiness**

Meroq is an educational/research project. It is designed to help understand model behavior, probability, risk, and evaluation quality. It is **not financial advice**.

---

## What Meroq Does Today

Meroq can:

- Accept a stock ticker such as `AAPL`, `MSFT`, `NVDA`, `TSLA`, or `SPY`
- Download historical OHLCV data with `yfinance`
- Save downloaded market data locally with SQLite
- Generate technical indicators:
  - Moving averages
  - RSI
  - MACD
  - Bollinger Bands
  - ATR
  - Volatility features
  - Stochastic oscillator
- Train a selected primary model
- Predict next-period up/down probability
- Show a bullish, neutral, or bearish signal
- Compare multiple models
- Run walk-forward validation
- Simulate strategy performance with transaction costs
- Run Monte Carlo risk simulation
- Show future price range estimates
- Separate product results from operational run details

---

## Stage 4.2 Highlights

Stage 4.2 is a stabilization checkpoint before adding NLP sentiment.

New or improved in this stage:

- Added **Analysis mode** selector:
  - Fast mode
  - Research mode
  - Full analysis mode
  - Custom
- Set safer defaults:
  - Primary model: XGBoost
  - Model comparison: Core fast
  - Monte Carlo simulation: On
  - Walk-forward loops: Off unless intentionally enabled
- Added clearer risk interpretation in the Risk Simulation tab
- Added risk-adjusted outlook to top metrics
- Kept live execution details in the **Run Details** tab
- Kept product-facing output in the **Results** tab
- Fixed duplicate Streamlit Plotly chart keys
- Replaced deprecated `use_container_width=True` with `width="stretch"`
- Added documentation for Git setup, usage, project status, and Stage 5 planning
- Added `.streamlit/config.toml` to disable Streamlit usage stats prompt locally

---

## Analysis Modes

### Fast mode

Best for normal development and UI testing.

Uses:

- XGBoost primary model
- Core fast model comparison
- Monte Carlo risk simulation
- No walk-forward loops by default

### Research mode

Best when you want more realistic model evaluation.

Uses:

- XGBoost primary model
- Core fast model comparison
- Primary walk-forward backtest enabled
- Limited recent folds for speed

### Full analysis mode

Best when you intentionally want a slow, heavier research run.

Uses:

- Advanced model comparison
- Primary walk-forward backtest
- Walk-forward comparison for all selected models

This can be slow, especially with ensemble models.

### Custom

Use this when you want to manually control all options.

---

## Model Families

Meroq currently supports:

1. Momentum Baseline
2. Logistic Regression
3. Random Forest
4. Extra Trees
5. HistGradientBoosting
6. XGBoost
7. LightGBM
8. CatBoost
9. Soft Voting Ensemble
10. Stacking Ensemble

The recommended everyday model is **XGBoost**. Ensemble models are useful for research but slower.

---

## App Layout

Meroq uses two top-level tabs.

### Results

The product-facing dashboard:

- Prediction
- Chart
- Risk Simulation
- Walk-forward Backtest
- Model Comparison
- Model Details
- Data Manager
- Production Roadmap

### Run Details

The operational view:

- Current stage
- Progress bar
- Completed/running/skipped stages
- Model training progress
- Walk-forward fold progress
- Execution logs
- Insights generated during the run

---

## Risk Simulation

The Risk Simulation tab uses Monte Carlo simulation to estimate possible future price ranges from recent volatility.

It shows:

- Median simulated final price
- 10th percentile final price
- 90th percentile final price
- Probability of positive return
- Probability of loss greater than 5%
- Probability of gain greater than 5%
- Expected max drawdown
- Final return distribution
- Optional sample simulated paths

This is a risk lens, not a guarantee.

---

## Default 10-Stock Universe

```text
AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA, AMD, JPM, SPY
```

---

## Tech Stack

- Python
- Streamlit
- yfinance
- pandas
- NumPy
- ta
- scikit-learn
- XGBoost
- LightGBM
- CatBoost
- Plotly
- SQLite

---

## Setup on Windows PowerShell

From the project folder:

```powershell
py -3.11 -m venv .venv
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the app:

```powershell
python -m streamlit run app.py
```

If needed:

```powershell
streamlit run app.py
```

---

## Suggested First Run

Use:

```text
Ticker: AAPL
History period: 5y
Interval: 1d
Analysis mode: Fast mode
Primary model: XGBoost
Model comparison set: Core fast
Monte Carlo risk simulation: On
Walk-forward backtests: Off
```

Then click **Run prediction**.

---

## Bootstrap Historical Data

To save max daily data for the default 10-stock universe:

```powershell
python scripts/bootstrap_watchlist.py --period max --interval 1d
```

To also save weekly data:

```powershell
python scripts/bootstrap_watchlist.py --period max --interval 1wk
```

This creates:

```text
data/market_data.sqlite
```

The database is generated data and is intentionally ignored by Git.

---

## Project Structure

```text
meroq/
├── app.py
├── requirements.txt
├── README.md
├── CHANGELOG.md
├── .gitignore
├── .streamlit/
│   └── config.toml
├── docs/
│   ├── GIT_WORKFLOW.md
│   ├── PROJECT_STATUS.md
│   ├── STAGE_5_NLP_PLAN.md
│   └── USAGE.md
├── scripts/
│   └── bootstrap_watchlist.py
├── src/
│   ├── __init__.py
│   ├── backtesting.py
│   ├── charts.py
│   ├── config.py
│   ├── data_loader.py
│   ├── features.py
│   ├── model.py
│   └── risk_simulation.py
└── data/
    └── market_data.sqlite  # created automatically, ignored by Git
```

---

## Documentation

Read these next:

- `CHANGELOG.md` — stage-by-stage project history
- `docs/USAGE.md` — how to use the app
- `docs/PROJECT_STATUS.md` — what is done and what is not done
- `docs/GIT_WORKFLOW.md` — suggested Git commit workflow
- `docs/STAGE_5_NLP_PLAN.md` — plan for adding news sentiment and FinBERT

---

## Important Disclaimer

This project is for education, research, and software engineering practice only.

It is **not financial advice**. Stock markets are noisy, uncertain, and affected by unpredictable events. Model outputs should be treated as experimental signals, not trading instructions.
