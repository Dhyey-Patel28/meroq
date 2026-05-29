# Model and risk notes

Meroq predicts direction probabilities, not guaranteed prices.

## Evaluation approach

- Simple chronological split for quick comparison
- Walk-forward validation for more realistic repeated future-window testing
- Transaction-cost-aware strategy metrics
- Buy-and-hold comparison

## Risk simulation

Monte Carlo simulation estimates future price ranges using recent volatility and selected drift assumptions. It is a risk lens, not a forecast guarantee.

## Common interpretation mistakes

- A high up-probability does not mean the stock will rise.
- A model can have acceptable classification metrics and still be unprofitable after costs.
- A strategy can look good on one ticker and fail on another.
- Sentiment can be useful context without being predictive by itself.
