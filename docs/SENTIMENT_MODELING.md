# Sentiment-Aware Modeling

Meroq now separates two related ideas:

1. **Signal fusion**: recent sentiment adjusts the latest model probability in a transparent, capped way.
2. **Sentiment-aware modeling**: lagged daily sentiment features are joined to the historical model frame and tested as additional model inputs.

The second approach is more rigorous, but it needs enough historical sentiment coverage. A few current headlines are not enough to train a reliable historical sentiment model.

## Why sentiment features are lagged

Daily sentiment is joined with a default one-day lag. This avoids using same-day headlines that may have been published after the market close. The goal is to reduce look-ahead bias.

## Added sentiment features

Meroq creates these experimental features:

- `sentiment_available`
- `sentiment_headline_count`
- `sentiment_mean`
- `sentiment_std`
- `positive_ratio`
- `negative_ratio`
- `neutral_ratio`
- `confidence_mean`

## How to interpret the experiment

The Sentiment Modeling tab compares:

- technical indicators only
- technical indicators plus lagged daily sentiment features

If coverage is low, Meroq will show the feature preview and readiness status instead of pretending the sentiment-trained model is reliable.

## What improves this over time

The local data layer should collect headlines and sentiment features over time. The experiment becomes more meaningful as aligned sentiment rows increase across many trading days.
