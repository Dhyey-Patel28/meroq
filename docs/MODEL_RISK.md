# Model Risk

Meroq is not financial advice.

Market direction prediction is noisy. Accuracy can look low even when a model provides useful ranking, probability, or risk context.

## Common risks

- Look-ahead bias
- Overfitting
- Unstable market regimes
- Transaction costs
- Survivorship bias
- News timing mismatch
- API/data quality issues

## Mitigations currently included

- Chronological train/test splits
- Walk-forward validation
- Transaction cost setting
- Baseline model comparison
- Risk simulation separate from deterministic prediction

## Next mitigations

- Sentiment-aware backtesting
- Regime-aware features
- Portfolio-level evaluation
- Data quality reports


## Sentiment overlay risk

Recent-news sentiment can be noisy, incomplete, duplicated, or unrelated to the ticker. Meroq therefore uses the sentiment layer as a capped overlay rather than a replacement for the base model.

The overlay should be interpreted as a context signal, not a trading recommendation. Full sentiment-aware model training requires historical sentiment features and walk-forward validation.
