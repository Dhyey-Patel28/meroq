# Frontend Migration

Meroq is migrating gradually from a Streamlit-first prototype toward a service-backed product architecture.

## Current architecture

```text
Streamlit app
FastAPI backend
Next.js frontend client
shared src/ analysis modules
SQLite local data/cache layer
```

Streamlit remains the best UI for research-heavy workflows. FastAPI exposes the reusable service layer. Next.js is becoming the product UI candidate.

## Migration principle

Do not rewrite the entire app at once. Move stable, user-facing workflows first:

1. Single ticker summary
2. Watchlist scan
3. Portfolio view
4. Report export
5. Forecast charting
6. Account/settings/deployment polish later

## Release 1.8.0 status

The frontend now includes API-backed pages for ticker analysis, watchlist scanning, and portfolio exposure. It is no longer only a static scaffold.

## Remaining gaps before replacing Streamlit

- Forecast range charts in React
- Model comparison and walk-forward views
- Report download workflow
- Data manager view
- More complete loading/progress states
- Frontend tests
- Deployment configuration
