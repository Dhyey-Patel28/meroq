from __future__ import annotations

from datetime import datetime, timezone
import os
from math import isfinite
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import DEFAULT_WATCHLIST, SUGGESTED_INTERVALS, SUGGESTED_PERIODS
from src.model import MODEL_LABELS, model_dependency_status
from src.news_sentiment import NEWS_SOURCE_OPTIONS, SENTIMENT_ENGINE_OPTIONS
from src.portfolio import build_portfolio_view, parse_portfolio_weights, portfolio_summary_sentence
from src.services import SingleTickerAnalysisRequest, run_single_ticker_analysis
from src.watchlist import scan_watchlist, summarize_watchlist_scan

APP_VERSION = "1.8.0"


class TickerAnalysisPayload(BaseModel):
    """Request payload for a single-ticker Meroq analysis."""

    ticker: str = Field(..., examples=["AAPL"])
    period: str = Field("5y", examples=["5y", "10y", "max"])
    interval: str = Field("1d", examples=["1d", "1wk"])
    model_name: str = Field("xgboost", examples=["xgboost", "random_forest"])
    include_risk: bool = True
    include_news: bool = True
    include_sentiment_fusion: bool = True
    news_source: str = "all_configured"
    sentiment_engine: str = "lightweight"
    max_news_items: int = Field(30, ge=0, le=100)
    news_lookback_days: int = Field(14, ge=1, le=90)
    cache_news_locally: bool = True
    force_news_refresh: bool = False
    simulation_horizon: int = Field(30, ge=5, le=252)
    simulation_paths: int = Field(500, ge=100, le=5000)
    volatility_window: int = Field(60, ge=5, le=252)
    drift_mode: str = "model_adjusted"
    sentiment_max_adjustment: float = Field(0.08, ge=0.0, le=0.20)
    return_details: bool = False


class WatchlistPayload(BaseModel):
    """Request payload for watchlist scanning."""

    tickers: list[str] = Field(default_factory=lambda: list(DEFAULT_WATCHLIST), examples=[["AAPL", "MSFT", "NVDA", "SPY"]])
    period: str = "5y"
    interval: str = "1d"
    news_source: str = "all_configured"
    sentiment_engine: str = "lightweight"
    max_news_items: int = Field(10, ge=0, le=50)
    days_back: int = Field(7, ge=1, le=90)
    include_sentiment: bool = True
    include_risk: bool = True
    risk_horizon: int = Field(30, ge=5, le=252)
    risk_paths: int = Field(300, ge=100, le=3000)
    volatility_window: int = Field(60, ge=5, le=252)
    drift_mode: str = "model_adjusted"
    max_adjustment: float = Field(0.08, ge=0.0, le=0.20)


class PortfolioPayload(WatchlistPayload):
    """Request payload for a portfolio view built from a watchlist scan."""

    weights: str = Field("", examples=["AAPL:30,MSFT:25,NVDA:25,SPY:20"])


def _sanitize(value: Any) -> Any:
    """Make pandas/numpy objects safe for JSON responses."""
    if value is None:
        return None
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if isfinite(value) else None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        v = float(value)
        return v if isfinite(v) else None
    if isinstance(value, (pd.Timestamp, datetime)):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    if isinstance(value, pd.DataFrame):
        return _records(value)
    if isinstance(value, pd.Series):
        return _sanitize(value.to_dict())
    if isinstance(value, dict):
        return {str(k): _sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize(v) for v in value]
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return str(value)


def _records(df: pd.DataFrame, max_rows: int | None = None) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    data = df.copy()
    if max_rows is not None:
        data = data.head(int(max_rows))
    for col in data.columns:
        if pd.api.types.is_datetime64_any_dtype(data[col]):
            data[col] = data[col].astype(str)
    return [_sanitize(row) for row in data.to_dict(orient="records")]


def create_app() -> FastAPI:
    app = FastAPI(
        title="Meroq API",
        version=APP_VERSION,
        description=(
            "Local API for Meroq ticker analysis, watchlist scanning, and portfolio views. "
            "This is intended as a migration bridge from Streamlit to a future Next.js frontend."
        ),
    )

    default_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ]
    configured_origins = os.getenv("MEROQ_API_ALLOWED_ORIGINS", "").strip()
    allowed_origins = (
        [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
        if configured_origins
        else default_origins
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "app": "Meroq API",
            "version": APP_VERSION,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    @app.get("/")
    def root() -> dict[str, Any]:
        return {
            "app": "Meroq API",
            "version": APP_VERSION,
            "status": "ok",
            "docs": "/docs",
            "health": "/health",
            "metadata": "/metadata",
        }

    @app.get("/metadata")
    def metadata() -> dict[str, Any]:
        return {
            "version": APP_VERSION,
            "models": MODEL_LABELS,
            "model_dependencies": _sanitize(model_dependency_status()),
            "news_sources": NEWS_SOURCE_OPTIONS,
            "sentiment_engines": SENTIMENT_ENGINE_OPTIONS,
            "default_watchlist": list(DEFAULT_WATCHLIST),
            "suggested_periods": list(SUGGESTED_PERIODS),
            "suggested_intervals": list(SUGGESTED_INTERVALS),
        }

    @app.post("/analysis/ticker")
    def analyze_ticker(payload: TickerAnalysisPayload) -> dict[str, Any]:
        try:
            request = SingleTickerAnalysisRequest(
                ticker=payload.ticker,
                period=payload.period,
                interval=payload.interval,
                model_name=payload.model_name,
                include_risk=payload.include_risk,
                simulation_horizon=payload.simulation_horizon,
                simulation_paths=payload.simulation_paths,
                volatility_window=payload.volatility_window,
                drift_mode=payload.drift_mode,
                include_news=payload.include_news,
                news_source=payload.news_source,
                sentiment_engine=payload.sentiment_engine,
                max_news_items=payload.max_news_items,
                news_lookback_days=payload.news_lookback_days,
                cache_news_locally=payload.cache_news_locally,
                force_news_refresh=payload.force_news_refresh,
                include_sentiment_fusion=payload.include_sentiment_fusion,
                sentiment_max_adjustment=payload.sentiment_max_adjustment,
            )
            result = run_single_ticker_analysis(request)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        response: dict[str, Any] = {
            "summary": _sanitize(result.get("summary", {})),
            "request": _sanitize(result.get("request", {})),
        }
        if payload.return_details:
            response["details"] = {
                "prediction": _sanitize(result.get("prediction", {})),
                "sentiment_summary": _sanitize(result.get("sentiment_summary", {})),
                "sentiment_fusion": _sanitize(result.get("sentiment_fusion", {})),
                "risk_summary": _sanitize((result.get("risk_results") or {}).get("summary", {})),
                "news_meta": _sanitize(result.get("news_meta", {})),
                "news_headlines": _records(result.get("sentiment"), max_rows=payload.max_news_items),
            }
        return response

    @app.get("/analysis/ticker/{ticker}")
    def analyze_ticker_get(
        ticker: str,
        period: str = Query("5y"),
        interval: str = Query("1d"),
        model_name: str = Query("xgboost"),
        include_news: bool = Query(True),
        include_risk: bool = Query(True),
    ) -> dict[str, Any]:
        payload = TickerAnalysisPayload(
            ticker=ticker,
            period=period,
            interval=interval,
            model_name=model_name,
            include_news=include_news,
            include_risk=include_risk,
        )
        return analyze_ticker(payload)

    @app.post("/watchlist/scan")
    def scan_watchlist_endpoint(payload: WatchlistPayload) -> dict[str, Any]:
        try:
            df = scan_watchlist(
                tickers=payload.tickers,
                period=payload.period,
                interval=payload.interval,
                news_source=payload.news_source,
                sentiment_engine=payload.sentiment_engine,
                max_news_items=payload.max_news_items,
                days_back=payload.days_back,
                include_sentiment=payload.include_sentiment,
                include_risk=payload.include_risk,
                risk_horizon=payload.risk_horizon,
                risk_paths=payload.risk_paths,
                volatility_window=payload.volatility_window,
                drift_mode=payload.drift_mode,
                max_adjustment=payload.max_adjustment,
            )
            summary = summarize_watchlist_scan(df)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"summary": _sanitize(summary), "rows": _records(df)}

    @app.post("/portfolio/analyze")
    def analyze_portfolio(payload: PortfolioPayload) -> dict[str, Any]:
        try:
            scan_df = scan_watchlist(
                tickers=payload.tickers,
                period=payload.period,
                interval=payload.interval,
                news_source=payload.news_source,
                sentiment_engine=payload.sentiment_engine,
                max_news_items=payload.max_news_items,
                days_back=payload.days_back,
                include_sentiment=payload.include_sentiment,
                include_risk=payload.include_risk,
                risk_horizon=payload.risk_horizon,
                risk_paths=payload.risk_paths,
                volatility_window=payload.volatility_window,
                drift_mode=payload.drift_mode,
                max_adjustment=payload.max_adjustment,
            )
            weights_df = parse_portfolio_weights(payload.tickers, payload.weights)
            holdings_df, portfolio_summary = build_portfolio_view(scan_df, weights_df)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "summary": _sanitize(portfolio_summary),
            "summary_sentence": portfolio_summary_sentence(portfolio_summary),
            "holdings": _records(holdings_df),
            "scan_rows": _records(scan_df),
        }

    return app


app = create_app()
