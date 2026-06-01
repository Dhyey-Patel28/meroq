# Portfolio Scenario Lab

Release 1.9.4 adds a local scenario lab to the portfolio command center.

The goal is to answer:

```text
How would the portfolio read change if the same holdings were weighted differently?
```

## Scenarios

The API returns three transparent scenario rows:

- `current` — uses the weights entered by the user.
- `equal_weight` — gives every successfully scanned holding the same weight.
- `research_weighted` — tilts toward stronger local Meroq scores and away from higher downside-risk readings.

These are diagnostic what-if views, not allocation advice.

## Scenario metrics

Each scenario includes:

```text
weighted_meroq_score
portfolio_grade
weighted_up_probability
weighted_downside_probability
weighted_sentiment_score
high_risk_weight
largest_position_ticker
largest_position_weight
concentration_score
concentration_label
score_delta
up_probability_delta
downside_delta
high_risk_weight_delta
summary
```

Deltas are measured against the current-weight baseline.

## Holding fields

Portfolio holdings now include scenario context when enough source fields are available:

```text
research_weight
research_weight_delta
allocation_review
```

The frontend uses these fields to show which holdings the research-weighted scenario would add to or trim.

## Free/local-first design

The scenario lab does not need broker sync, paid fundamentals, sector data, or a portfolio optimizer. It reuses existing scan fields:

- Meroq Score
- final up probability
- target-aware sentiment score
- downside risk probability
- risk label

## Limitations

The scenario lab does not model taxes, transaction costs, position size constraints, sector exposure, covariance, beta, options, or liquidity. It should be treated as a research diagnostic layer only.
