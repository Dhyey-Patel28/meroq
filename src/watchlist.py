from __future__ import annotations

from typing import Callable, Iterable

import numpy as np
import pandas as pd

from src.data_loader import fetch_price_data
from src.features import add_technical_features, build_model_frame
from src.model import predict_latest, train_classifier
from src.news_sentiment import analyze_news_sentiment, fetch_news_for_ticker, summarize_sentiment
from src.risk_simulation import risk_label, simulate_price_paths
from src.signal_fusion import fuse_prediction_with_sentiment


def _clip_score(value: float) -> float:
    return float(max(0.0, min(100.0, value)))


def compute_meroq_score(
    final_up_probability: float,
    sentiment_score: float = 0.0,
    risk_positive_probability: float | None = None,
    risk_loss_gt_5pct: float | None = None,
    rsi_14: float | None = None,
    close_sma20_ratio: float | None = None,
) -> float:
    """Combine directional probability, sentiment, trend, and risk into a transparent 0-100 score.

    This score is intentionally simple. It is designed for ranking watchlist names,
    not for autonomous trading. The formula favors higher model probability,
    constructive sentiment, positive trend, and lower downside-risk probability.
    """
    score = 50.0
    score += (float(final_up_probability) - 0.5) * 90.0
    score += float(sentiment_score or 0.0) * 10.0

    if risk_positive_probability is not None and np.isfinite(risk_positive_probability):
        score += (float(risk_positive_probability) - 0.5) * 20.0
    if risk_loss_gt_5pct is not None and np.isfinite(risk_loss_gt_5pct):
        score -= float(risk_loss_gt_5pct) * 18.0

    if close_sma20_ratio is not None and np.isfinite(close_sma20_ratio):
        score += max(-5.0, min(5.0, float(close_sma20_ratio) * 120.0))

    if rsi_14 is not None and np.isfinite(rsi_14):
        # Penalize extreme overbought/oversold readings slightly because the
        # directional model can already capture momentum. This keeps the watchlist
        # score from blindly chasing extremes.
        if float(rsi_14) > 75:
            score -= 3.0
        elif float(rsi_14) < 25:
            score -= 2.0

    return round(_clip_score(score), 2)


def _progress(progress_callback: Callable[[dict], None] | None, payload: dict) -> None:
    if progress_callback is not None:
        progress_callback(payload)


def scan_single_ticker(
    ticker: str,
    period: str = "5y",
    interval: str = "1d",
    news_source: str = "all_configured",
    sentiment_engine: str = "lightweight",
    max_news_items: int = 10,
    days_back: int = 7,
    include_sentiment: bool = True,
    include_risk: bool = True,
    risk_horizon: int = 30,
    risk_paths: int = 500,
    volatility_window: int = 60,
    drift_mode: str = "model_adjusted",
    max_adjustment: float = 0.08,
    n_estimators: int = 80,
) -> dict:
    """Run a fast local Meroq scan for one ticker."""
    symbol = ticker.upper().strip()
    raw_df = fetch_price_data(symbol, period=period, interval=interval)
    feature_df = add_technical_features(raw_df).dropna().reset_index(drop=True)
    model_frame = build_model_frame(raw_df)
    min_rows = 120 if interval == "1wk" else 180

    results = train_classifier(
        model_frame=model_frame,
        model_name="xgboost",
        min_rows=min_rows,
        n_estimators=int(n_estimators),
    )
    latest_row = feature_df.iloc[-1]
    prediction = predict_latest(results["model"], latest_row)

    latest_close = float(raw_df["Close"].iloc[-1])
    latest_date = pd.to_datetime(raw_df["Date"].iloc[-1]).date().isoformat()
    return_1d = float(latest_row.get("return_1d", np.nan))
    rsi_14 = float(latest_row.get("rsi_14", np.nan))
    close_sma20_ratio = float(latest_row.get("close_sma20_ratio", np.nan))

    sentiment_summary = {"available": False, "overall_label": "Skipped", "average_score": 0.0, "headline_count": 0}
    news_meta = {"source_used": "skipped"}
    if include_sentiment:
        news_df, news_meta = fetch_news_for_ticker(
            ticker=symbol,
            source=news_source,
            max_items=int(max_news_items),
            days_back=int(days_back),
            use_cache=True,
            force_refresh=False,
        )
        sentiment_df = analyze_news_sentiment(news_df, engine=sentiment_engine)
        sentiment_summary = summarize_sentiment(sentiment_df)

    fusion = fuse_prediction_with_sentiment(
        prediction,
        sentiment_summary,
        max_adjustment=float(max_adjustment),
    )
    final_probability = float(fusion.get("adjusted_up_probability", prediction["up_probability"])) if fusion.get("available") else float(prediction["up_probability"])
    final_signal = fusion.get("signal", prediction["signal"]) if fusion.get("available") else prediction["signal"]

    risk_summary = {}
    risk_label_text = "Skipped"
    if include_risk:
        risk_results = simulate_price_paths(
            price_df=raw_df,
            horizon=int(risk_horizon),
            n_paths=int(risk_paths),
            volatility_window=int(volatility_window),
            drift_mode=drift_mode,
            model_up_probability=float(prediction["up_probability"]),
            random_seed=42,
        )
        risk_summary = risk_results["summary"]
        risk_label_text = risk_label(risk_summary)

    risk_positive = float(risk_summary.get("probability_positive_return", np.nan)) if risk_summary else np.nan
    risk_loss = float(risk_summary.get("probability_loss_gt_5pct", np.nan)) if risk_summary else np.nan
    sentiment_score = float(sentiment_summary.get("average_score", 0.0) or 0.0)

    score = compute_meroq_score(
        final_up_probability=final_probability,
        sentiment_score=sentiment_score,
        risk_positive_probability=risk_positive,
        risk_loss_gt_5pct=risk_loss,
        rsi_14=rsi_14,
        close_sma20_ratio=close_sma20_ratio,
    )

    return {
        "ticker": symbol,
        "status": "ok",
        "latest_close": round(latest_close, 2),
        "latest_date": latest_date,
        "return_1d": return_1d,
        "rsi_14": rsi_14,
        "close_sma20_ratio": close_sma20_ratio,
        "base_signal": prediction["signal"],
        "base_up_probability": float(prediction["up_probability"]),
        "sentiment_label": sentiment_summary.get("overall_label", "Unavailable"),
        "sentiment_score": sentiment_score,
        "headline_count": int(sentiment_summary.get("headline_count", 0) or 0),
        "sentiment_source": news_meta.get("source_used", "unknown"),
        "final_signal": final_signal,
        "final_up_probability": final_probability,
        "risk_label": risk_label_text,
        "risk_positive_probability": risk_positive,
        "risk_loss_gt_5pct": risk_loss,
        "risk_median_return": float(risk_summary.get("median_return", np.nan)) if risk_summary else np.nan,
        "meroq_score": score,
        "model_accuracy": float(results["metrics"].get("accuracy", np.nan)),
        "model_roc_auc": float(results["metrics"].get("roc_auc", np.nan)) if pd.notna(results["metrics"].get("roc_auc")) else np.nan,
    }


def scan_watchlist(
    tickers: Iterable[str],
    period: str = "5y",
    interval: str = "1d",
    news_source: str = "all_configured",
    sentiment_engine: str = "lightweight",
    max_news_items: int = 10,
    days_back: int = 7,
    include_sentiment: bool = True,
    include_risk: bool = True,
    risk_horizon: int = 30,
    risk_paths: int = 500,
    volatility_window: int = 60,
    drift_mode: str = "model_adjusted",
    max_adjustment: float = 0.08,
    progress_callback: Callable[[dict], None] | None = None,
) -> pd.DataFrame:
    """Scan a list of tickers and return a ranked watchlist DataFrame."""
    symbols = [str(x).upper().strip() for x in tickers if str(x).strip()]
    symbols = list(dict.fromkeys(symbols))
    rows: list[dict] = []
    total = len(symbols)

    for idx, symbol in enumerate(symbols, start=1):
        _progress(progress_callback, {"status": "running", "ticker": symbol, "index": idx, "total": total, "detail": "starting"})
        try:
            row = scan_single_ticker(
                ticker=symbol,
                period=period,
                interval=interval,
                news_source=news_source,
                sentiment_engine=sentiment_engine,
                max_news_items=max_news_items,
                days_back=days_back,
                include_sentiment=include_sentiment,
                include_risk=include_risk,
                risk_horizon=risk_horizon,
                risk_paths=risk_paths,
                volatility_window=volatility_window,
                drift_mode=drift_mode,
                max_adjustment=max_adjustment,
            )
            rows.append(row)
            _progress(progress_callback, {"status": "complete", "ticker": symbol, "index": idx, "total": total, "detail": f"score {row.get('meroq_score')}"})
        except Exception as exc:  # Keep one bad ticker from breaking the whole scan.
            rows.append({"ticker": symbol, "status": "failed", "error": str(exc)})
            _progress(progress_callback, {"status": "failed", "ticker": symbol, "index": idx, "total": total, "detail": str(exc)})

    df = pd.DataFrame(rows)
    if not df.empty and "meroq_score" in df.columns:
        df = df.sort_values(["status", "meroq_score"], ascending=[True, False], na_position="last").reset_index(drop=True)
    return df


def summarize_watchlist_scan(df: pd.DataFrame) -> dict:
    """Summarize a watchlist scan for UI cards."""
    if df is None or df.empty:
        return {
            "tickers_scanned": 0,
            "bullish_count": 0,
            "positive_sentiment_count": 0,
            "high_risk_count": 0,
        }

    ok = df[df.get("status", "") == "ok"].copy()
    if ok.empty:
        return {
            "tickers_scanned": 0,
            "bullish_count": 0,
            "positive_sentiment_count": 0,
            "high_risk_count": 0,
        }

    return {
        "tickers_scanned": int(len(ok)),
        "bullish_count": int((ok["final_signal"].astype(str).str.lower() == "bullish").sum()) if "final_signal" in ok else 0,
        "positive_sentiment_count": int((ok["sentiment_label"].astype(str).str.lower() == "positive").sum()) if "sentiment_label" in ok else 0,
        "high_risk_count": int((ok["risk_label"].astype(str).str.contains("High", case=False, na=False)).sum()) if "risk_label" in ok else 0,
    }
