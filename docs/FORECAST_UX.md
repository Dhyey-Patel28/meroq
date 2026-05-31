# Forecast-first Prediction UX

Meroq's Prediction page is designed for users who want a clear answer before they inspect model internals.

## Product principle

The main Prediction page should answer four questions:

1. What is the current price?
2. What does Meroq expect the future range to look like?
3. How confident is the signal?
4. Why did the system say that?

## What changed

The Prediction tab now prioritizes:

- Historical close price.
- A future median forecast path.
- A likely forecast range using the 10th and 90th Monte Carlo percentiles.
- A plain-English explanation of the model, sentiment, and risk inputs.
- Beginner-friendly technical interpretations for momentum, trend pressure, and volatility.

The old close-vs-probability chart is still useful for model diagnostics, but it is no longer the first thing users see. It now lives under an Advanced diagnostics expander.

## Why forecasts are shown as ranges

Meroq should not pretend it can predict an exact future stock price. A range is more honest and better aligned with uncertainty. The median path is the center estimate, while the 10th and 90th percentiles show plausible downside and upside outcomes under the simulation assumptions.

## Remaining improvement ideas

- Add a 5-day / 30-day forecast toggle.
- Add a tooltip explaining that the chart is simulation-based, not a guaranteed price target.
- Let users switch between recent 1-year history and full selected history on the forecast chart.
- Add benchmark context such as SPY comparison.

## 1.4.2 cleanup

The Prediction tab should not show model-diagnostic charts by default. Historical probability diagnostics are now kept in Model Details so the primary Prediction tab stays focused on current close, forecast range, confidence, and plain-English reasoning.

Technical explanations are also collapsed behind hover/help text and advanced expanders instead of being displayed as permanent table columns.
