# Frontend Product UI

Release 1.8.1 upgrades the Next.js folder from a static scaffold to an API-connected product client.

## What is included

The frontend now calls the local FastAPI backend for:

- ticker analysis through `POST /analysis/ticker`
- watchlist scans through `POST /watchlist/scan`
- portfolio exposure through `POST /portfolio/analyze`

The goal is not to replace Streamlit immediately. The goal is to validate the API contract and begin shaping a cleaner long-term product interface.

## Local workflow

Terminal 1:

```powershell
python scripts/run_api.py --reload
```

Terminal 2:

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## Current frontend pages

| Page | Purpose |
|---|---|
| `/` | Backend status and navigation |
| `/ticker` | Single ticker analysis with signal, probability, risk, and headlines |
| `/watchlist` | Ranked multi-ticker scan |
| `/portfolio` | Weighted portfolio exposure view |

## Still handled better by Streamlit

Streamlit remains the complete research dashboard for:

- full model comparison
- walk-forward backtesting
- Monte Carlo chart details
- sentiment modeling diagnostics
- report generation
- data manager inspection

## Next frontend improvements

Recommended next frontend work:

1. Add charting for forecast range and watchlist ranking.
2. Add report download from the API or a frontend report builder.
3. Add persisted user settings for ticker universe and weights.
4. Add better loading progress for long local model calls.
5. Add a lightweight frontend test suite.


## 1.8.1 HCD update

- Ticker analysis now surfaces headline cards with `Open source article ↗` links.
- Data tables render URL fields as links instead of raw text.
- The frontend copy now follows a conclusion → evidence → source inspection flow.
- D3.js is planned separately in `docs/D3_VISUALIZATION_ROADMAP.md`.

## Forecast-first ticker page

The frontend ticker workflow should show a human-readable answer before implementation detail:

1. signal and final probability,
2. decision read: direction, evidence, risk,
3. forecast range from Monte Carlo percentiles,
4. source-linked headlines,
5. raw headline tables only after disclosure.

The forecast chart uses risk percentile data returned by the FastAPI endpoint when `return_details=true`.
