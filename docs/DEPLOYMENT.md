# Deployment

Meroq is currently designed as a local-first research application. It can be shared publicly as a GitHub project, but API keys and generated data should remain local.

## Local development

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Secrets

Optional provider keys should live in `.env` for local development.

```env
FINNHUB_API_KEY=
NEWSAPI_API_KEY=
```

Do not commit `.env`.

For hosted Streamlit deployments, use the platform's secrets manager instead of committing environment files. Keep NewsAPI disabled for public hosted demos unless the usage is permitted by your plan.

## Public demo mode

Recommended public/demo settings:

- Analysis mode: Fast mode
- Primary model: XGBoost
- Model comparison: Core fast
- Walk-forward comparison: Off
- Sentiment engine: Lightweight financial lexicon
- News source: yfinance or user-provided key only
- Risk simulation paths: 500 to 1,000
- Watchlist size: 5 to 10 symbols

This keeps the app responsive and avoids exposing private API keys.

## Generated data

These files are local runtime artifacts and should not be committed:

- `data/market_data.sqlite`
- `data/news_cache.sqlite`
- `*.db`
- `*.sqlite`
- `.venv/`
- Hugging Face cache directories

The repository includes `data/.gitkeep` only to preserve the folder structure.

## Deployment checklist

Before sharing or deploying:

1. Confirm `.env` is not tracked by Git.
2. Run `git status` and confirm no local database files appear.
3. Use Fast mode as the default demo experience.
4. Keep API-dependent features optional.
5. Add screenshots/GIFs to the README after the UI stabilizes.
6. Add a clear disclaimer that Meroq is research software, not financial advice.

## Near-term hosted demo strategy

The safest public demo is a Streamlit app with:

- yfinance-only news by default
- lightweight sentiment by default
- optional user-provided API keys disabled unless the platform supports secure secrets
- no paid APIs
- no persisted user secrets
- small watchlist defaults
