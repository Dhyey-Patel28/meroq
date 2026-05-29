# Research notebooks

The notebooks are intended for experiments outside the Streamlit UI.

## Included notebooks

- `01_price_feature_audit.ipynb` — inspect downloaded data and engineered features
- `02_news_sentiment_research.ipynb` — test news providers and sentiment engines
- `03_model_comparison_research.ipynb` — compare models outside the UI
- `04_risk_simulation_research.ipynb` — inspect Monte Carlo assumptions and output

## Setup

```powershell
python -m pip install -r requirements-research.txt
python -m ipykernel install --user --name meroq --display-name "Python (Meroq)"
```

These notebooks are original Meroq notebooks and are safe to commit. Do not commit downloaded datasets, model weights, `.env`, or local SQLite databases.
