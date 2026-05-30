# Frontend Migration Plan

Meroq should not be migrated to React/Next.js immediately. The current Streamlit app is the right surface for fast model iteration, chart debugging, and research workflows.

A React or Next.js frontend becomes valuable after the data/model boundary is stable.

## Current architecture

```text
Streamlit UI
  -> data loader
  -> feature engineering
  -> model comparison
  -> risk simulation
  -> news sentiment
  -> reporting
  -> local SQLite stores
```

This is efficient for prototyping but not ideal for a polished SaaS-style product.

## Target architecture

```text
Next.js frontend
  -> FastAPI backend
      -> prediction service
      -> watchlist scan service
      -> sentiment service
      -> risk simulation service
      -> report generation service
      -> local/PostgreSQL data layer
```

## Why not migrate now?

Migrating now would slow down modeling work. The app still benefits from quick Python-first iteration:

- model features change frequently
- sentiment sources are still evolving
- report structure is still being refined
- watchlist scoring is still experimental
- deployment and caching behavior are still local-first

## When to migrate

Start the migration when these are stable:

1. Prediction API contract
2. Watchlist scan output schema
3. Sentiment summary schema
4. Risk simulation summary schema
5. Report payload schema
6. Public/demo deployment requirements

## Migration phases

### Phase 1: Extract service functions

Keep Streamlit, but ensure each major capability returns clean dictionaries/dataframes:

- `run_single_ticker_analysis`
- `run_watchlist_scan`
- `run_sentiment_analysis`
- `run_risk_simulation`
- `build_report`

### Phase 2: Add FastAPI

Expose stable endpoints:

```text
POST /analyze
POST /watchlist/scan
POST /sentiment
POST /risk/simulate
POST /report
GET /health
```

### Phase 3: Build Next.js UI

Build a polished frontend with:

- dashboard cards
- watchlist table
- report export page
- clearer loading states
- model/risk/sentiment explainability panels

### Phase 4: Move persistence out of local SQLite if needed

For local users, SQLite remains fine. For hosted/shared use, use PostgreSQL or another managed database.

## Recommendation

Keep Streamlit through the next few releases. Use it as the research workbench. Add FastAPI before React/Next.js. Then build a Next.js UI only when the backend is stable enough to be a product API.
