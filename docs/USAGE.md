# Usage Guide

## Recommended Development Settings

Use these while building and testing:

```text
Analysis mode: Fast mode
Ticker: AAPL
History period: 5y
Interval: 1d
Primary model: XGBoost
Model comparison set: Core fast
Run Monte Carlo risk simulation: On
Run primary walk-forward backtest: Off
Run walk-forward comparison for all models: Off
```

This gives a fast, stable product run.

## When to Use Research Mode

Use **Research mode** when you want a more realistic evaluation of the primary model.

It enables primary walk-forward backtesting with a limited number of folds.

## When to Use Full Analysis Mode

Use **Full analysis mode** only when you are okay waiting.

It can run advanced models and walk-forward comparisons across many models. This is useful for research but not ideal for quick UI testing.

## Good Test Cases

Daily:

```text
AAPL / 5y / 1d
SPY / 10y / 1d
NVDA / 10y / 1d
```

Weekly:

```text
AAPL / max / 1wk
SPY / max / 1wk
NVDA / max / 1wk
```

Weekly intervals have fewer rows, so use `10y` or `max`.

## Interpreting the Prediction

The main prediction answers:

```text
What is the model-estimated probability that the next trading period closes higher?
```

It does **not** say the exact future price.

## Interpreting Risk Simulation

Monte Carlo simulation answers:

```text
Given recent volatility, what range of future prices is plausible?
```

Important outputs:

- 10th percentile: downside scenario
- 50th percentile: median scenario
- 90th percentile: upside scenario
- Loss > 5% probability: downside risk
- Expected max drawdown: average worst drop inside simulated paths

## Interpreting Walk-Forward Backtesting

Walk-forward validation is more realistic than a single train/test split.

It repeatedly:

1. Trains on past data
2. Predicts the next unseen future window
3. Moves forward
4. Combines all out-of-sample predictions

Use this to judge whether a model is robust.

## If the App Feels Slow

Use:

```text
Analysis mode: Fast mode
Primary model: XGBoost
Model comparison set: Core fast
Walk-forward comparison: Off
```

Avoid Stacking Ensemble while iterating quickly.
