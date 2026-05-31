# D3 Visualization Roadmap

D3 is not required for the current Streamlit interface. It becomes valuable when the Next.js frontend becomes the primary UI.

## Candidate D3 views

1. **Forecast fan chart**: historical close, median forecast, and 10th/90th percentile bands with hover tooltips.
2. **Watchlist signal matrix**: tickers by model, sentiment, risk, and score with a clear strength/risk scale.
3. **Portfolio exposure map**: position weight, downside contribution, sentiment contribution, and concentration alerts.
4. **News impact timeline**: headlines on a timeline with sentiment score and original source link.

## Rule

Use D3 only when it improves understanding. Avoid decorative charts that do not help the user interpret the analysis.
