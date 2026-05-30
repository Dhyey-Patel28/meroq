from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd


def _pct(value: Any, default: str = "N/A") -> str:
    try:
        if value is None:
            return default
        return f"{float(value):.1%}"
    except Exception:
        return default


def _num(value: Any, digits: int = 2, default: str = "N/A") -> str:
    try:
        if value is None:
            return default
        return f"{float(value):,.{digits}f}"
    except Exception:
        return default


def _safe(value: Any, default: str = "N/A") -> str:
    if value is None:
        return default
    text = str(value)
    return text if text.strip() else default


def _top_rows_as_markdown(df: pd.DataFrame | None, columns: list[str], n: int = 5) -> str:
    if df is None or df.empty:
        return "_No rows available._"

    available = [col for col in columns if col in df.columns]
    if not available:
        return "_No matching columns available._"

    view = df[available].head(n).copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: round(float(x), 4) if pd.notna(x) else x)
    return view.to_markdown(index=False)


def build_insight_report(
    ticker: str,
    latest_close: float,
    latest_date: str,
    analysis_mode: str,
    selected_model_label: str,
    prediction: dict,
    model_metrics: dict,
    sentiment_fusion: dict | None = None,
    sentiment_summary: dict | None = None,
    risk_summary: dict | None = None,
    watchlist_df: pd.DataFrame | None = None,
    model_comparison_df: pd.DataFrame | None = None,
    walk_forward_results: dict | None = None,
) -> str:
    """Build a concise Markdown report for the current Meroq run."""

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    base_probability = float(prediction.get("up_probability", 0.0) or 0.0)
    base_signal = _safe(prediction.get("signal"))

    adjusted_probability = base_probability
    adjusted_signal = base_signal
    adjustment = 0.0
    if sentiment_fusion and sentiment_fusion.get("available"):
        adjusted_probability = float(sentiment_fusion.get("adjusted_up_probability", base_probability) or base_probability)
        adjusted_signal = _safe(sentiment_fusion.get("signal"), base_signal)
        adjustment = float(sentiment_fusion.get("adjustment", 0.0) or 0.0)

    sentiment_label = "Skipped"
    sentiment_score = None
    headline_count = None
    sentiment_confidence = None
    if sentiment_summary and sentiment_summary.get("available"):
        sentiment_label = _safe(sentiment_summary.get("overall_label"))
        sentiment_score = sentiment_summary.get("average_score")
        headline_count = sentiment_summary.get("headline_count")
        sentiment_confidence = sentiment_summary.get("confidence")

    risk_label = "Skipped"
    positive_return_probability = None
    downside_probability = None
    median_return = None
    expected_drawdown = None
    if risk_summary:
        positive_return_probability = risk_summary.get("probability_positive_return")
        downside_probability = risk_summary.get("probability_loss_gt_5pct")
        median_return = risk_summary.get("median_return")
        expected_drawdown = risk_summary.get("expected_max_drawdown")
        if downside_probability is not None:
            if float(downside_probability) >= 0.35:
                risk_label = "Elevated downside risk"
            elif float(positive_return_probability or 0.0) >= 0.58 and float(downside_probability) <= 0.22:
                risk_label = "Constructive risk profile"
            else:
                risk_label = "Balanced risk profile"

    wf_accuracy = "Skipped"
    if walk_forward_results:
        wf_accuracy = _pct(walk_forward_results.get("classification_metrics", {}).get("accuracy"))

    report = f"""# Meroq Insight Report: {ticker.upper()}

Generated: {generated_at}

## Executive Summary

| Item | Value |
|---|---:|
| Latest close | ${_num(latest_close)} |
| Latest data date | {_safe(latest_date)} |
| Analysis mode | {_safe(analysis_mode)} |
| Primary model | {_safe(selected_model_label)} |
| Base signal | {base_signal} |
| Base up probability | {_pct(base_probability)} |
| Sentiment-aware signal | {adjusted_signal} |
| Sentiment-aware up probability | {_pct(adjusted_probability)} |
| Sentiment adjustment | {adjustment:+.2%} |
| News sentiment | {sentiment_label} |
| Risk profile | {risk_label} |
| Walk-forward accuracy | {wf_accuracy} |

## Model Signal

Meroq's selected model is **{_safe(selected_model_label)}**. The model produced a **{base_signal}** base signal with a **{_pct(base_probability)}** probability of an upward next-period move.

| Metric | Value |
|---|---:|
| Simple split accuracy | {_pct(model_metrics.get("accuracy"))} |
| Simple split F1 | {_pct(model_metrics.get("f1"))} |
| Simple split ROC-AUC | {_num(model_metrics.get("roc_auc"), 3)} |
| Train rows | {_safe(model_metrics.get("train_rows"))} |
| Test rows | {_safe(model_metrics.get("test_rows"))} |

## Sentiment Overlay

| Item | Value |
|---|---:|
| Overall news sentiment | {sentiment_label} |
| Average sentiment score | {_num(sentiment_score, 3)} |
| Headlines scored | {_safe(headline_count)} |
| Sentiment confidence | {_pct(sentiment_confidence)} |
| Probability adjustment | {adjustment:+.2%} |
| Adjusted up probability | {_pct(adjusted_probability)} |

## Risk Simulation

| Item | Value |
|---|---:|
| Risk profile | {risk_label} |
| Median simulated return | {_pct(median_return)} |
| Probability of positive return | {_pct(positive_return_probability)} |
| Probability of loss greater than 5% | {_pct(downside_probability)} |
| Expected max drawdown | {_pct(expected_drawdown)} |

## Watchlist Highlights

{_top_rows_as_markdown(
    watchlist_df,
    [
        "ticker",
        "latest_close",
        "base_signal",
        "base_up_probability",
        "sentiment_label",
        "final_signal",
        "final_up_probability",
        "risk_label",
        "meroq_score",
    ],
    n=10,
)}

## Model Comparison Snapshot

{_top_rows_as_markdown(
    model_comparison_df,
    ["model", "status", "accuracy", "f1", "roc_auc", "train_rows", "test_rows"],
    n=10,
)}

## Interpretation Notes

- Meroq is an educational/research system, not financial advice.
- The sentiment overlay is intentionally conservative; it can tilt the model signal but should not dominate it.
- Monte Carlo simulation describes a range of possible outcomes based on historical volatility; it is not a price guarantee.
- Walk-forward validation is more realistic than a simple split, but it can still overstate future performance if assumptions change.
"""
    return report
