# D3 Visualization Roadmap

D3.js should be added when the Next.js frontend becomes the primary visualization surface.

## Why not add it immediately?

The current frontend can already call the FastAPI endpoints and display useful product views. Adding D3 too early would increase complexity before the data contracts and page flows are stable.

## Candidate D3 views

1. **Forecast fan chart**
   - Historical close price plus simulated future percentile bands.

2. **Watchlist risk matrix**
   - X-axis: final up probability.
   - Y-axis: downside-risk probability.
   - Bubble size: Meroq Score.
   - Color: sentiment label.

3. **Portfolio contribution map**
   - Weighted downside contribution by holding.
   - Shows which position contributes most to portfolio risk.

4. **News sentiment timeline**
   - Articles positioned by publication time and sentiment score.
   - Clickable article nodes opening the source page.

## Suggested implementation path

- Keep Plotly/Streamlit for research diagnostics.
- Add D3 only to the Next.js frontend.
- Use D3 for custom interactions where normal tables/cards are insufficient.
- Keep source links and accessibility labels in every interactive visualization.

## Near-term rule

Do not add D3 only for decoration. Add it when the frontend needs interactions that simple SVG cannot provide, such as brushing, linked tooltips, cross-filtering, or animated portfolio contribution views.

Release 1.8.2 intentionally uses a lightweight SVG forecast band first. This validates the data contract before introducing a heavier visualization dependency.
