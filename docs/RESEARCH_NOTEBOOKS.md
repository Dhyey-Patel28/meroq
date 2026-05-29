# Research Notebooks

The notebooks are intended for reproducible exploration, not production app logic.

## Included notebooks

- `01_price_feature_audit.ipynb`
- `02_news_sentiment_research.ipynb`
- `03_model_comparison_research.ipynb`
- `04_risk_simulation_research.ipynb`

## Suggested workflow

1. Use the Streamlit app to validate end-to-end behavior.
2. Use notebooks to investigate specific assumptions.
3. Promote only stable findings into `src/`.


## 05 Sentiment signal fusion

`notebooks/05_sentiment_signal_fusion.ipynb` explains how recent-news sentiment can be used as a conservative overlay on top of the base model probability.
