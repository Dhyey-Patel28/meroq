# Meroq Grades

Meroq Grades turn local research signals into compact A-F labels for faster scanning.

Grades are not buy/sell recommendations. They are attention labels built from locally available data:

- Meroq Score
- directional probability
- momentum / trend
- Monte Carlo downside-risk estimate
- target-aware news sentiment
- model confidence
- data quality

## Component grades

- **Momentum**: recent trend context from technical features.
- **Risk**: downside-risk and positive-return probability from Monte Carlo simulation.
- **Sentiment**: target-aware recent-news sentiment.
- **Model confidence**: simple split quality and distance from a 50/50 probability.
- **Data quality**: whether the run has enough usable data and supporting evidence.

## Interpretation

- **A/B**: constructive research candidate.
- **C**: balanced/watchlist candidate.
- **D/F**: caution or weak current setup.

Grades should be read together with source articles, forecast range, risk simulation, and model diagnostics.
