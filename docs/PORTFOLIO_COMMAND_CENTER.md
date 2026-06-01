# Portfolio Command Center

Release 1.9.3 upgrades the portfolio view from a weighted table into a command center.

The goal is to answer:

```text
What is carrying the portfolio read, and what deserves attention first?
```

## Inputs

The command center uses only free/local inputs already available in Meroq:

- watchlist scan rows
- optional user-supplied weights
- local Meroq Score and Meroq Grade
- target-aware sentiment summary
- Monte Carlo downside-risk fields
- model probability fields

No broker sync, paid fundamentals, or paid institutional feed is required.

## New summary fields

`POST /portfolio/analyze` now includes portfolio-level fields such as:

```text
largest_position_ticker
largest_position_weight
concentration_score
concentration_label
portfolio_health_label
grade_distribution
top_score_contributors
top_risk_contributors
weakest_holdings
highest_risk_holdings
portfolio_alerts
```

These fields are designed for user triage, not trading automation.

## Concentration labels

Meroq labels allocation concentration as:

- `Concentrated`
- `Moderate`
- `Diversified`

The label uses the largest holding weight and a simple Herfindahl-style concentration score:

```text
concentration_score = sum(weight²)
```

This is transparent and intentionally simple.

## Contributor lists

The portfolio response ranks:

- top Meroq Score contributors
- top downside contributors
- weakest holdings by Meroq Score
- highest-risk holdings by loss-probability estimate

This helps a user see whether the aggregate portfolio read is coming from broad support or from one dominant holding.

## Portfolio alerts

`portfolio_alerts` contains short command-center cards with:

```text
title
severity
ticker
metric
detail
```

The frontend renders these as insight cards above the holdings table.

## Limitations

This is still a transparent diagnostic layer. It does not yet model:

- cross-asset covariance
- beta to SPY or QQQ
- sectors/industries
- options exposure
- taxes
- liquidity
- broker positions

Those are future upgrades. The 1.9.3 release focuses on making existing local signals more understandable and action-oriented.

## Scenario lab

Release 1.9.4 adds a scenario lab above the charts. It compares current weights, equal weights, and a research-weighted diagnostic scenario. The frontend also shows scenario adds/trims based on `research_weight_delta`.

The scenario lab is intentionally framed as a what-if diagnostic, not allocation advice.
