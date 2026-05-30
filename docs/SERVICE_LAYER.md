# Service Layer

Meroq started as a Streamlit app, but the analysis logic should not be trapped inside UI callbacks. Release 1.3.0 adds a reusable service layer that can be called from scripts, notebooks, tests, Streamlit, or a future FastAPI backend.

## Why this matters

The service layer is the bridge between the current local product and a future production architecture:

```text
Streamlit UI today
    ↓
src.services reusable analysis functions
    ↓
price, feature, model, news, sentiment, risk, report modules
```

Later, the same service functions can sit behind:

```text
Next.js frontend
    ↓
FastAPI backend
    ↓
src.services
```

## Main entry point

```python
from src.services import SingleTickerAnalysisRequest, run_single_ticker_analysis

request = SingleTickerAnalysisRequest(
    ticker="AAPL",
    period="5y",
    interval="1d",
    model_name="xgboost",
    include_risk=True,
    include_news=True,
    news_source="all_configured",
    sentiment_engine="lightweight",
)

result = run_single_ticker_analysis(request)
print(result["summary"])
```

## Command-line usage

```bash
python scripts/analyze_ticker.py --ticker AAPL --period 5y --interval 1d
```

JSON output:

```bash
python scripts/analyze_ticker.py --ticker PLAY --period 5y --json --output reports/play_summary.json
```

Skip optional subsystems:

```bash
python scripts/analyze_ticker.py --ticker HOG --no-news --no-risk
```

## Returned artifacts

`run_single_ticker_analysis()` returns:

| Key | Description |
|---|---|
| `summary` | JSON-friendly single-ticker summary |
| `raw_prices` | downloaded OHLCV DataFrame |
| `features` | technical indicator DataFrame |
| `model_frame` | ML-ready feature/target DataFrame |
| `model_result` | trained model, metrics, test data, probabilities |
| `prediction` | latest base model signal |
| `risk_results` | Monte Carlo risk simulation artifacts |
| `news` | fetched headline table |
| `news_meta` | news source and matching metadata |
| `sentiment` | headline-level sentiment table |
| `sentiment_summary` | aggregated sentiment summary |
| `daily_sentiment` | daily sentiment features |
| `sentiment_fusion` | sentiment-aware signal overlay |

## Design rules

- Keep API/service outputs JSON-friendly where possible.
- Keep DataFrames available for notebooks and Streamlit charts.
- Do not store `.env` secrets in the result payload.
- Keep optional subsystems skippable so tests and demos can run quickly.
- Avoid making Streamlit the only way to run the analysis.
