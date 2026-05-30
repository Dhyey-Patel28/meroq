# Portfolio Risk and Exposure

Meroq 1.2.0 adds a portfolio-level view built on top of the existing watchlist scan.

The goal is to answer a different question from the single-ticker page:

> If these tickers are viewed together as a portfolio, where is the exposure concentrated and what is the combined risk/signal profile?

## What the portfolio view does

The Portfolio tab uses the scanned watchlist rows and optional user weights to calculate:

- weighted Meroq Score
- weighted up-probability
- weighted downside-risk probability
- weighted sentiment score
- weighted one-day return
- bullish/bearish exposure by weight
- positive-sentiment exposure by weight
- high-risk exposure by weight

It also shows charts for:

- portfolio weights
- weighted downside contribution by holding

## Weighting options

By default, the portfolio view uses equal weights across the scanned tickers.

Users can also provide custom weights in the sidebar:

```text
AAPL:40, MSFT:25, SPY:35
```

Both percentages and decimals are accepted. Missing tickers receive equal residual weight when possible, and all weights are normalized to sum to 1.

## Limitations

This is not a full institutional portfolio optimizer. It does not yet model:

- asset covariance
- sector exposure
- beta to market indexes
- options or derivatives exposure
- tax impact
- intraday liquidity
- position sizing constraints

The view is intentionally transparent and diagnostic. It is designed to help users understand how the watchlist scan looks when converted into weighted exposure.

## Future improvements

Good next upgrades include:

- correlation matrix
- beta exposure vs. SPY
- sector/industry exposure
- portfolio-level Monte Carlo simulation using covariance
- drawdown decomposition by holding
- user-uploaded portfolio CSV support
