# Sentiment-Aware Signal Fusion

Meroq separates the base machine-learning prediction from the recent-news sentiment overlay.

The base model still produces the primary probability:

```text
P(up next period)
```

The sentiment layer then applies a capped adjustment using recent headline sentiment:

```text
adjusted_probability = base_probability + capped_sentiment_adjustment
```

## Why this design

Recent news is useful context, but it should not dominate a price model. The fusion layer is intentionally conservative and transparent:

- the base model probability remains visible;
- the sentiment adjustment is shown in percentage points;
- the final sentiment-aware signal is shown separately;
- no hidden paid inference API is used;
- the app still works when no news or no Hugging Face model is available.

## Adjustment inputs

The current overlay uses:

- average sentiment score;
- sentiment confidence;
- number of usable headlines;
- ensemble model agreement when available;
- a user-configurable maximum adjustment cap.

The default cap is 8 percentage points. For example, a 53% base probability and a +2.2 point sentiment adjustment becomes 55.2%.

## What this is not

This is not yet a fully retrained sentiment model. A fully historical sentiment model requires a dated sentiment feature table that can be joined to each historical OHLCV row without look-ahead leakage.

The current layer is a transparent signal overlay for current analysis.

## Next modeling upgrade

The next deeper upgrade is historical sentiment feature training:

1. persist daily sentiment feature rows;
2. join sentiment features to OHLCV rows by date;
3. train models with and without sentiment features;
4. compare walk-forward performance;
5. keep all joins time-safe to avoid future-data leakage.
