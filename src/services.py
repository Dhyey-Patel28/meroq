from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from src.data_loader import fetch_price_data
from src.features import add_technical_features, build_model_frame
from src.grades import build_grade_bundle
from src.watchlist import compute_meroq_score
from src.model import MODEL_LABELS, predict_latest, train_classifier
from src.news_sentiment import analyze_news_sentiment, fetch_news_for_ticker, summarize_sentiment
from src.risk_simulation import risk_label, simulate_price_paths
from src.sentiment_features import aggregate_daily_sentiment
from src.signal_fusion import fuse_prediction_with_sentiment
from src.ticker_brief import build_ticker_brief


@dataclass(frozen=True)
class SingleTickerAnalysisRequest:
    """Configuration for a reusable single-ticker Meroq analysis run.

    This is intentionally UI-agnostic so it can be used by Streamlit today and
    by a future FastAPI endpoint later.
    """

    ticker: str
    period: str = "5y"
    interval: str = "1d"
    model_name: str = "xgboost"
    model_n_estimators: int = 180
    min_model_rows: int = 120
    include_risk: bool = True
    simulation_horizon: int = 30
    simulation_paths: int = 1000
    volatility_window: int = 60
    drift_mode: str = "model_adjusted"
    include_news: bool = True
    news_source: str = "all_configured"
    sentiment_engine: str = "lightweight"
    max_news_items: int = 30
    news_lookback_days: int = 14
    cache_news_locally: bool = True
    force_news_refresh: bool = False
    include_sentiment_fusion: bool = True
    sentiment_max_adjustment: float = 0.08

    def normalized_ticker(self) -> str:
        return self.ticker.strip().upper()


@dataclass(frozen=True)
class SingleTickerAnalysisSummary:
    """Compact, JSON-friendly summary of a Meroq analysis run."""

    ticker: str
    generated_at_utc: str
    latest_close: float
    latest_data_date: str
    model_name: str
    model_label: str
    base_signal: str
    base_up_probability: float
    final_signal: str
    final_up_probability: float
    sentiment_adjustment_pct_points: float | None
    news_sentiment_label: str | None
    news_sentiment_score: float | None
    headlines_analyzed: int
    risk_label: str | None
    risk_probability_positive_return: float | None
    risk_probability_loss_gt_5pct: float | None
    meroq_score: float
    meroq_grade: str
    meroq_grade_label: str
    momentum_grade: str
    risk_grade: str
    sentiment_grade: str
    model_confidence_grade: str
    data_quality_grade: str
    grade_summary: str
    simple_split_accuracy: float
    simple_split_f1: float
    simple_split_roc_auc: float | None
    train_rows: int
    test_rows: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _latest_data_date(raw_df: pd.DataFrame) -> str:
    if raw_df.empty or "Date" not in raw_df.columns:
        return "unknown"
    return str(pd.to_datetime(raw_df["Date"].iloc[-1]).date())


def _metric_or_none(metrics: dict[str, Any], key: str) -> float | None:
    value = metrics.get(key)
    try:
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def run_single_ticker_analysis(request: SingleTickerAnalysisRequest) -> dict[str, Any]:
    """Run the core Meroq single-ticker analysis without Streamlit.

    Returns a dictionary with both machine-readable summaries and optional
    DataFrames. The shape is stable enough for CLI tools and a future API layer,
    while still keeping the full analysis artifacts available for notebooks.
    """
    ticker = request.normalized_ticker()
    if not ticker:
        raise ValueError("Ticker cannot be empty.")

    raw_df = fetch_price_data(ticker=ticker, period=request.period, interval=request.interval)
    feature_df = add_technical_features(raw_df).dropna().reset_index(drop=True)
    model_frame = build_model_frame(raw_df)
    if feature_df.empty or model_frame.empty:
        raise ValueError("No usable feature rows were created. Try a longer history period.")

    model_result = train_classifier(
        model_frame=model_frame,
        model_name=request.model_name,
        min_rows=int(request.min_model_rows),
        n_estimators=int(request.model_n_estimators),
    )
    latest_row = feature_df.iloc[-1]
    prediction = predict_latest(model_result["model"], latest_row)

    risk_results = None
    risk_name = None
    if request.include_risk:
        risk_results = simulate_price_paths(
            raw_df,
            horizon=int(request.simulation_horizon),
            n_paths=int(request.simulation_paths),
            volatility_window=int(request.volatility_window),
            drift_mode=request.drift_mode,
            model_up_probability=float(prediction["up_probability"]),
        )
        risk_name = risk_label(risk_results["summary"])

    news_df = pd.DataFrame()
    news_meta: dict[str, Any] = {}
    sentiment_df = pd.DataFrame()
    sentiment_summary: dict[str, Any] | None = None
    daily_sentiment = pd.DataFrame()
    if request.include_news:
        news_df, news_meta = fetch_news_for_ticker(
            ticker=ticker,
            source=request.news_source,
            max_items=int(request.max_news_items),
            days_back=int(request.news_lookback_days),
            use_cache=bool(request.cache_news_locally),
            force_refresh=bool(request.force_news_refresh),
        )
        sentiment_df = analyze_news_sentiment(news_df, engine=request.sentiment_engine)
        sentiment_summary = summarize_sentiment(sentiment_df)
        if not sentiment_df.empty:
            daily_sentiment = aggregate_daily_sentiment(sentiment_df, ticker=ticker)

    sentiment_fusion = None
    if request.include_sentiment_fusion and sentiment_summary is not None:
        sentiment_fusion = fuse_prediction_with_sentiment(
            prediction,
            sentiment_summary,
            max_adjustment=float(request.sentiment_max_adjustment),
        )

    final_signal = prediction["signal"]
    final_up_probability = float(prediction["up_probability"])
    sentiment_adjustment = None
    if sentiment_fusion and sentiment_fusion.get("available"):
        final_signal = str(sentiment_fusion["signal"])
        final_up_probability = float(sentiment_fusion["adjusted_up_probability"])
        sentiment_adjustment = float(sentiment_fusion["adjustment_pct_points"])

    metrics = model_result["metrics"]
    latest_return_1d = _metric_or_none(latest_row.to_dict(), "return_1d")
    latest_rsi_14 = _metric_or_none(latest_row.to_dict(), "rsi_14")
    latest_close_sma20_ratio = _metric_or_none(latest_row.to_dict(), "close_sma20_ratio")
    risk_summary = (risk_results or {}).get("summary", {})
    risk_positive = _metric_or_none(risk_summary, "probability_positive_return")
    risk_loss = _metric_or_none(risk_summary, "probability_loss_gt_5pct")
    sentiment_score = _metric_or_none(sentiment_summary or {}, "average_score") if sentiment_summary else 0.0
    headline_count = int((sentiment_summary or {}).get("headline_count", 0) if sentiment_summary else 0)
    meroq_score = compute_meroq_score(
        final_up_probability=final_up_probability,
        sentiment_score=sentiment_score or 0.0,
        risk_positive_probability=risk_positive,
        risk_loss_gt_5pct=risk_loss,
        rsi_14=latest_rsi_14,
        close_sma20_ratio=latest_close_sma20_ratio,
    )
    grade_bundle = build_grade_bundle(
        meroq_score=meroq_score,
        final_up_probability=final_up_probability,
        sentiment_score=sentiment_score,
        headline_count=headline_count,
        risk_loss_gt_5pct=risk_loss,
        risk_positive_probability=risk_positive,
        close_sma20_ratio=latest_close_sma20_ratio,
        rsi_14=latest_rsi_14,
        model_roc_auc=metrics.get("roc_auc"),
        model_accuracy=metrics.get("accuracy"),
        status="ok",
    )
    summary = SingleTickerAnalysisSummary(
        ticker=ticker,
        generated_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        latest_close=float(pd.to_numeric(raw_df["Close"], errors="coerce").dropna().iloc[-1]),
        latest_data_date=_latest_data_date(raw_df),
        model_name=str(model_result.get("model_name", request.model_name)),
        model_label=str(model_result.get("model_label", MODEL_LABELS.get(request.model_name, request.model_name))),
        base_signal=str(prediction["signal"]),
        base_up_probability=float(prediction["up_probability"]),
        final_signal=final_signal,
        final_up_probability=final_up_probability,
        sentiment_adjustment_pct_points=sentiment_adjustment,
        news_sentiment_label=(sentiment_summary or {}).get("display_label", (sentiment_summary or {}).get("overall_label")) if sentiment_summary else None,
        news_sentiment_score=_metric_or_none(sentiment_summary or {}, "average_score") if sentiment_summary else None,
        headlines_analyzed=int((sentiment_summary or {}).get("headline_count", 0) if sentiment_summary else 0),
        risk_label=risk_name,
        risk_probability_positive_return=risk_positive,
        risk_probability_loss_gt_5pct=risk_loss,
        meroq_score=meroq_score,
        meroq_grade=str(grade_bundle["meroq_grade"]),
        meroq_grade_label=str(grade_bundle["meroq_grade_label"]),
        momentum_grade=str(grade_bundle["momentum_grade"]),
        risk_grade=str(grade_bundle["risk_grade"]),
        sentiment_grade=str(grade_bundle["sentiment_grade"]),
        model_confidence_grade=str(grade_bundle["model_confidence_grade"]),
        data_quality_grade=str(grade_bundle["data_quality_grade"]),
        grade_summary=str(grade_bundle["grade_summary"]),
        simple_split_accuracy=float(metrics["accuracy"]),
        simple_split_f1=float(metrics["f1"]),
        simple_split_roc_auc=_metric_or_none(metrics, "roc_auc"),
        train_rows=int(metrics.get("train_rows", 0)),
        test_rows=int(metrics.get("test_rows", 0)),
    )

    summary_dict = summary.as_dict()
    brief = build_ticker_brief(summary_dict, risk_summary)

    return {
        "request": asdict(request),
        "summary": summary_dict,
        "brief": brief,
        "raw_prices": raw_df,
        "features": feature_df,
        "model_frame": model_frame,
        "model_result": model_result,
        "prediction": prediction,
        "risk_results": risk_results,
        "news": news_df,
        "news_meta": news_meta,
        "sentiment": sentiment_df,
        "sentiment_summary": sentiment_summary,
        "daily_sentiment": daily_sentiment,
        "sentiment_fusion": sentiment_fusion,
    }


def single_ticker_summary_frame(result: dict[str, Any]) -> pd.DataFrame:
    """Return a one-row DataFrame for CLI, notebooks, and future API adapters."""
    summary = result.get("summary", {}) if result else {}
    return pd.DataFrame([summary]) if summary else pd.DataFrame()
