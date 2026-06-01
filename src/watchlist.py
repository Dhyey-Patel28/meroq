from __future__ import annotations

from typing import Callable, Iterable

import numpy as np
import pandas as pd

from src.data_loader import fetch_price_data
from src.features import add_technical_features, build_model_frame
from src.grades import build_grade_bundle
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


_GRADE_RANK = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return number if np.isfinite(number) else default


def _grade_rank(value: object) -> int:
    return _GRADE_RANK.get(str(value or "").upper(), 0)


def _watchlist_bucket(row: dict) -> str:
    """Classify a scanned symbol into a plain-English screener queue."""
    if str(row.get("status", "")).lower() != "ok":
        return "Data issue"

    score = _safe_float(row.get("meroq_score"))
    risk_loss = _safe_float(row.get("risk_loss_gt_5pct"), default=np.nan)
    up_probability = _safe_float(row.get("final_up_probability"), default=0.5)
    grade = str(row.get("meroq_grade") or "").upper()
    sentiment = str(row.get("sentiment_label") or "").lower()
    risk_label_text = str(row.get("risk_label") or "").lower()

    high_risk = "high" in risk_label_text or (np.isfinite(risk_loss) and risk_loss >= 0.42)
    cautionary = any(token in sentiment for token in ["caution", "negative", "bearish"])

    if high_risk or cautionary or score < 45 or grade in {"D", "F"}:
        return "Risk review"
    if score >= 70 and grade in {"A", "B"} and up_probability >= 0.56:
        return "Research queue"
    if up_probability >= 0.55 or score >= 62 or grade in {"B", "C"}:
        return "Momentum watch"
    return "Low priority"


def _research_priority(row: dict) -> int:
    """Return a stable 0-100 priority score for watchlist triage."""
    if str(row.get("status", "")).lower() != "ok":
        return 0

    priority = _safe_float(row.get("meroq_score"))
    priority += (_safe_float(row.get("final_up_probability"), 0.5) - 0.5) * 28.0
    priority += _safe_float(row.get("sentiment_score")) * 8.0
    priority += (_grade_rank(row.get("meroq_grade")) - 3) * 3.0

    risk_loss = _safe_float(row.get("risk_loss_gt_5pct"), default=np.nan)
    if np.isfinite(risk_loss):
        priority -= risk_loss * 18.0

    sentiment_label = str(row.get("sentiment_label") or "").lower()
    if "caution" in sentiment_label or "negative" in sentiment_label:
        priority -= 8.0

    if _watchlist_bucket(row) == "Risk review":
        priority -= 4.0

    return int(round(max(0.0, min(100.0, priority))))


def _scan_note(row: dict) -> str:
    """Create a short note explaining why the row landed in its queue."""
    if str(row.get("status", "")).lower() != "ok":
        return str(row.get("error") or "Data unavailable")

    ticker = str(row.get("ticker") or "This name")
    bucket = str(row.get("watchlist_bucket") or _watchlist_bucket(row))
    grade = str(row.get("meroq_grade") or "N/A")
    score = _safe_float(row.get("meroq_score"))
    up_probability = _safe_float(row.get("final_up_probability"), default=0.5)
    risk_loss = _safe_float(row.get("risk_loss_gt_5pct"), default=np.nan)
    sentiment = str(row.get("sentiment_label") or "Neutral")

    if bucket == "Research queue":
        return f"{ticker} combines a {grade} grade, {score:.0f} score, and {up_probability:.0%} up probability."
    if bucket == "Momentum watch":
        return f"{ticker} has a constructive setup but needs confirmation before deeper research."
    if bucket == "Risk review":
        risk_text = f" with {risk_loss:.0%} simulated >5% downside risk" if np.isfinite(risk_loss) else ""
        return f"{ticker} needs review{risk_text}; sentiment is {sentiment}."
    return f"{ticker} is currently lower priority versus stronger ranked names."


def enrich_watchlist_row(row: dict) -> dict:
    """Add screener-friendly classification fields to a scan row."""
    enriched = dict(row)
    if str(enriched.get("status", "")).lower() != "ok":
        enriched.setdefault("watchlist_bucket", "Data issue")
        enriched.setdefault("research_priority", 0)
        enriched.setdefault("evidence_count", 0)
        enriched.setdefault("scan_note", str(enriched.get("error") or "Data unavailable"))
        return enriched

    enriched["watchlist_bucket"] = _watchlist_bucket(enriched)
    enriched["research_priority"] = _research_priority(enriched)
    enriched["evidence_count"] = int(_safe_float(enriched.get("headline_count"), 0))
    enriched["scan_note"] = _scan_note(enriched)
    return enriched


def _records_from_df(df: pd.DataFrame, limit: int = 5, sort_by: str = "research_priority", ascending: bool = False) -> list[dict]:
    if df is None or df.empty:
        return []
    data = df.copy()
    if sort_by in data.columns:
        data = data.sort_values(sort_by, ascending=ascending, na_position="last")
    return data.head(limit).replace({np.nan: None}).to_dict(orient="records")


def _grade_distribution(df: pd.DataFrame) -> list[dict]:
    if df is None or df.empty or "meroq_grade" not in df.columns:
        return []
    total = max(1, len(df))
    rows = []
    for grade in ["A", "B", "C", "D", "F", "N/A"]:
        count = int((df["meroq_grade"].fillna("N/A").astype(str).str.upper() == grade).sum())
        if count:
            rows.append({"grade": grade, "count": count, "share": round(count / total, 4)})
    return rows


def build_watchlist_alerts(summary: dict) -> list[dict]:
    """Build concise alert cards for the watchlist command center."""
    alerts: list[dict] = []
    ready_count = int(summary.get("ready_count", 0) or 0)
    if ready_count == 0:
        return alerts

    top = (summary.get("top_research_candidates") or [])[:1]
    if top:
        row = top[0]
        alerts.append(
            {
                "title": "Best research candidate",
                "severity": "positive",
                "ticker": row.get("ticker"),
                "detail": row.get("scan_note") or "Highest priority row in the completed scan.",
            }
        )

    risk_count = int(summary.get("risk_review_count", 0) or 0)
    if risk_count:
        risk = (summary.get("risk_review") or [])[:1]
        alerts.append(
            {
                "title": "Risk review queue",
                "severity": "warning",
                "ticker": risk[0].get("ticker") if risk else None,
                "detail": f"{risk_count} ready name{'s' if risk_count != 1 else ''} landed in risk review before deeper research.",
            }
        )

    issue_count = int(summary.get("issue_count", 0) or 0)
    if issue_count:
        alerts.append(
            {
                "title": "Data cleanup needed",
                "severity": "warning",
                "ticker": None,
                "detail": f"{issue_count} ticker{'s' if issue_count != 1 else ''} could not be analyzed and should be checked or replaced.",
            }
        )

    if not alerts:
        alerts.append(
            {
                "title": "Balanced scan",
                "severity": "neutral",
                "ticker": None,
                "detail": "No single queue dominates this scan. Compare scores, risk, and news evidence before choosing deep dives.",
            }
        )
    return alerts


def summarize_watchlist_command_center(df: pd.DataFrame) -> dict:
    """Summarize a completed or in-progress watchlist as a screener command center."""
    if df is None or df.empty:
        summary = {
            "tickers_scanned": 0,
            "ready_count": 0,
            "issue_count": 0,
            "research_queue_count": 0,
            "momentum_watch_count": 0,
            "risk_review_count": 0,
            "low_priority_count": 0,
            "average_meroq_score": None,
            "best_candidate_ticker": None,
            "grade_distribution": [],
            "top_research_candidates": [],
            "momentum_watch": [],
            "risk_review": [],
            "sentiment_watch": [],
            "data_issues": [],
        }
        summary["scan_alerts"] = []
        summary["screener_summary"] = "Run a watchlist scan to build a research queue."
        return summary

    data = pd.DataFrame([enrich_watchlist_row(row) for row in df.to_dict(orient="records")])
    ok = data[data.get("status", "").astype(str).str.lower() == "ok"].copy() if "status" in data else data.iloc[0:0].copy()
    issues = data[data.get("status", "").astype(str).str.lower() == "failed"].copy() if "status" in data else data.iloc[0:0].copy()

    research = ok[ok.get("watchlist_bucket", "") == "Research queue"].copy() if not ok.empty else ok.copy()
    momentum = ok[ok.get("watchlist_bucket", "") == "Momentum watch"].copy() if not ok.empty else ok.copy()
    risk = ok[ok.get("watchlist_bucket", "") == "Risk review"].copy() if not ok.empty else ok.copy()
    low = ok[ok.get("watchlist_bucket", "") == "Low priority"].copy() if not ok.empty else ok.copy()
    sentiment_watch = ok[ok.get("sentiment_label", "").astype(str).str.contains("Caution|Negative|Bearish", case=False, na=False)].copy() if not ok.empty and "sentiment_label" in ok else ok.iloc[0:0].copy()

    average_score = float(ok["meroq_score"].mean()) if not ok.empty and "meroq_score" in ok else None
    top_candidates = _records_from_df(research if not research.empty else ok, limit=5, sort_by="research_priority", ascending=False)
    summary = {
        "tickers_scanned": int(len(data)),
        "ready_count": int(len(ok)),
        "issue_count": int(len(issues)),
        "research_queue_count": int(len(research)),
        "momentum_watch_count": int(len(momentum)),
        "risk_review_count": int(len(risk)),
        "low_priority_count": int(len(low)),
        "average_meroq_score": round(average_score, 2) if average_score is not None and np.isfinite(average_score) else None,
        "best_candidate_ticker": top_candidates[0].get("ticker") if top_candidates else None,
        "grade_distribution": _grade_distribution(ok),
        "top_research_candidates": top_candidates,
        "momentum_watch": _records_from_df(momentum, limit=5, sort_by="research_priority", ascending=False),
        "risk_review": _records_from_df(risk, limit=5, sort_by="risk_loss_gt_5pct", ascending=False),
        "sentiment_watch": _records_from_df(sentiment_watch, limit=5, sort_by="research_priority", ascending=False),
        "data_issues": _records_from_df(issues, limit=8, sort_by="ticker", ascending=True),
    }
    summary["scan_alerts"] = build_watchlist_alerts(summary)
    if summary["best_candidate_ticker"]:
        summary["screener_summary"] = (
            f"{summary['best_candidate_ticker']} leads the research queue; "
            f"{summary['risk_review_count']} ready name{'s' if summary['risk_review_count'] != 1 else ''} need risk review."
        )
    else:
        summary["screener_summary"] = "No high-priority research candidates yet; review risk and data-issue queues first."
    return summary


def _progress(progress_callback: Callable[[dict], None] | None, payload: dict) -> None:
    if progress_callback is not None:
        progress_callback(payload)


def friendly_scan_error(ticker: str, exc: Exception | str) -> str:
    """Convert provider/model exceptions into a concise user-facing message."""
    symbol = str(ticker).upper().strip()
    raw = str(exc).strip() or "No price data returned."
    lowered = raw.lower()
    if any(token in lowered for token in ["possibly delisted", "not found", "no timezone found", "no price data", "quote not found"]):
        return (
            f"Unable to load data for {symbol}. The symbol may be delisted, renamed, unsupported by the provider, or temporarily unavailable."
        )
    if "empty" in lowered and "data" in lowered:
        return f"Unable to load data for {symbol}. The provider returned no usable price history."
    return f"Unable to load data for {symbol}. {raw}"


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
    metrics = results["metrics"]
    grades = build_grade_bundle(
        meroq_score=score,
        final_up_probability=final_probability,
        sentiment_score=sentiment_score,
        headline_count=sentiment_summary.get("headline_count", 0),
        risk_loss_gt_5pct=risk_loss,
        risk_positive_probability=risk_positive,
        close_sma20_ratio=close_sma20_ratio,
        rsi_14=rsi_14,
        model_roc_auc=metrics.get("roc_auc"),
        model_accuracy=metrics.get("accuracy"),
        status="ok",
    )

    row = {
        "ticker": symbol,
        "status": "ok",
        "latest_close": round(latest_close, 2),
        "latest_date": latest_date,
        "return_1d": return_1d,
        "rsi_14": rsi_14,
        "close_sma20_ratio": close_sma20_ratio,
        "base_signal": prediction["signal"],
        "base_up_probability": float(prediction["up_probability"]),
        "sentiment_label": sentiment_summary.get("display_label", sentiment_summary.get("overall_label", "Unavailable")),
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
        **grades,
        "model_accuracy": float(metrics.get("accuracy", np.nan)),
        "model_roc_auc": float(metrics.get("roc_auc", np.nan)) if pd.notna(metrics.get("roc_auc")) else np.nan,
    }
    return enrich_watchlist_row(row)


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
            message = friendly_scan_error(symbol, exc)
            rows.append(enrich_watchlist_row({"ticker": symbol, "status": "failed", "error": message}))
            _progress(progress_callback, {"status": "failed", "ticker": symbol, "index": idx, "total": total, "detail": message})

    df = pd.DataFrame(rows)
    if not df.empty and "meroq_score" in df.columns:
        df = df.sort_values(["status", "meroq_score"], ascending=[True, False], na_position="last").reset_index(drop=True)
    return df


def summarize_watchlist_scan(df: pd.DataFrame) -> dict:
    """Summarize a watchlist scan for UI cards and screener command-center panels."""
    summary = summarize_watchlist_command_center(df)
    # Backward-compatible aliases retained for older UI/API consumers.
    summary["bullish_count"] = 0
    summary["positive_sentiment_count"] = 0
    summary["high_risk_count"] = 0

    if df is not None and not df.empty:
        ok = df[df.get("status", "") == "ok"].copy()
        if not ok.empty:
            summary["bullish_count"] = int((ok["final_signal"].astype(str).str.lower() == "bullish").sum()) if "final_signal" in ok else 0
            summary["positive_sentiment_count"] = int((ok["sentiment_label"].astype(str).str.lower() == "positive").sum()) if "sentiment_label" in ok else 0
            summary["high_risk_count"] = int((ok["risk_label"].astype(str).str.contains("High", case=False, na=False)).sum()) if "risk_label" in ok else 0
    return summary
