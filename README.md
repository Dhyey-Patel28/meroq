# Meroq

Meroq is a local-first market intelligence dashboard for stock movement research. It combines technical indicators, model comparison, walk-forward backtesting, Monte Carlo risk simulation, and recent-news sentiment analysis.

Meroq is built for research and education. It is not financial advice and should not be used as an automated trading system.

## Highlights

- Interactive Streamlit dashboard
- Historical OHLCV data through `yfinance`
- Local SQLite storage for downloaded market data
- Technical indicators including RSI, MACD, Bollinger Bands, ATR, volatility, stochastic oscillator, and moving averages
- Multiple model families: momentum baseline, logistic regression, random forest, Extra Trees, HistGradientBoosting, XGBoost, LightGBM, CatBoost, soft voting, and stacking
- Chronological train/test evaluation
- Walk-forward validation with transaction costs
- Monte Carlo price-path risk simulation
- Recent-news aggregation from yfinance plus optional user-provided Finnhub and NewsAPI keys
- Local Hugging Face financial sentiment models, with lightweight fallback
- Research notebooks for feature review, sentiment testing, model comparison, and risk simulation

## Current release

**Release 0.5.2 — Sentiment intelligence and project cleanup**

This release improves the news layer and cleans the public repo structure:

- Adds an “All configured sources” news mode
- Adds local news caching to reduce repeated API calls
- Supports yfinance, Finnhub, and NewsAPI source aggregation
- Keeps NewsAPI labeled as a development/testing-only provider
- Uses local Hugging Face financial NLP models when installed
- Keeps a lightweight fallback sentiment scorer so the app still runs without NLP dependencies
- Adds professional project documentation and reproducible notebooks
- Removes process-oriented stage planning files from the public repo

## Quick start

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local Streamlit URL and run a ticker such as `AAPL`, `MSFT`, `NVDA`, `TSLA`, or `SPY`.

## Optional local NLP models

Install the NLP extras only when you want Hugging Face sentiment models:

```powershell
python -m pip install -r requirements-nlp.txt
```

The first run of a Hugging Face sentiment engine may take time because model files are downloaded and cached locally. Public Hugging Face models do not require a Hugging Face API key for normal local inference.

Available sentiment engines:

- Lightweight financial lexicon
- `ProsusAI/finbert`
- `yiyanghkust/finbert-tone`
- `mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis`
- Finance sentiment ensemble

## Optional API keys

Meroq runs without API keys. Optional news providers can be enabled with a local `.env` file.

```powershell
Copy-Item .\.env.example .\.env
notepad .env
```

Example:

```env
FINNHUB_API_KEY=your_finnhub_key_here
NEWSAPI_API_KEY=your_newsapi_key_here
```

Rules:

- Do not commit `.env`
- Do not paste API keys into the app source code
- Use your own provider keys
- Follow each provider’s terms of service
- NewsAPI’s free Developer plan is intended for local development/testing, not hosted production usage

## Research notebooks

Install notebook dependencies:

```powershell
python -m pip install -r requirements-research.txt
python -m ipykernel install --user --name meroq --display-name "Python (Meroq)"
```

Notebook directory:

```text
notebooks/
├── 01_price_feature_audit.ipynb
├── 02_news_sentiment_research.ipynb
├── 03_model_comparison_research.ipynb
└── 04_risk_simulation_research.ipynb
```

These notebooks are original project notebooks for Meroq. They are not copied Kaggle notebooks. They are structured so you can later adapt public Kaggle datasets or Hugging Face datasets while keeping the main application clean.

## Project structure

```text
meroq/
├── app.py
├── requirements.txt
├── requirements-nlp.txt
├── requirements-research.txt
├── .env.example
├── data/
│   └── .gitkeep
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATA_SOURCES.md
│   ├── SENTIMENT_SYSTEM.md
│   ├── MODEL_RISK.md
│   └── RESEARCH_NOTEBOOKS.md
├── notebooks/
├── scripts/
└── src/
```

## Recommended app settings

For fast iteration:

- Analysis mode: Fast mode
- Primary model: XGBoost
- Model comparison set: Core fast
- News source: All configured sources
- Sentiment engine: Lightweight or FinBERT
- Walk-forward backtest: Off

For deeper research:

- Analysis mode: Research mode
- News source: All configured sources
- Sentiment engine: Finance sentiment ensemble
- Primary walk-forward: On
- Max recent folds: 6–10

## Disclaimer

Meroq is an educational research tool. Market data, news data, sentiment models, and simulations can be wrong or incomplete. Outputs should be interpreted as research signals, not investment recommendations.
