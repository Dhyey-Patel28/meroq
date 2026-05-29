from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


def _clip_probability(value: float) -> float:
    return float(np.clip(value, 0.02, 0.98))


def _signal_from_probability(probability: float) -> str:
    if probability >= 0.57:
        return "Bullish"
    if probability <= 0.43:
        return "Bearish"
    return "Neutral"


def _confidence_label(probability: float, adjustment: float, sentiment_confidence: float) -> str:
    distance = abs(probability - 0.5)
    if distance >= 0.12 and sentiment_confidence >= 0.65:
        return "Higher"
    if distance >= 0.07 or abs(adjustment) >= 0.03:
        return "Moderate"
    return "Low"


def sentiment_adjustment(
    sentiment_summary: dict[str, Any] | None,
    max_adjustment: float = 0.08,
) -> dict[str, Any]:
    """
    Convert a recent-news sentiment summary into a conservative probability adjustment.

    This is intentionally small. It is a signal overlay, not a retrained model.
    """
    if not sentiment_summary or not sentiment_summary.get("available"):
        return {
            "available": False,
            "adjustment": 0.0,
            "average_score": 0.0,
            "confidence": 0.0,
            "headline_count": 0,
            "headline_factor": 0.0,
            "agreement": None,
            "reason": "No usable sentiment summary.",
        }

    average_score = float(sentiment_summary.get("average_score", 0.0) or 0.0)
    confidence = float(sentiment_summary.get("confidence", 0.0) or 0.0)
    headline_count = int(sentiment_summary.get("headline_count", 0) or 0)
    agreement = sentiment_summary.get("agreement")

    # 10+ headlines gets full weight; fewer headlines are down-weighted.
    headline_factor = min(1.0, max(0.0, headline_count / 10.0))

    # If ensemble agreement is available, use it as an extra reliability factor.
    agreement_factor = 1.0
    if agreement is not None:
        try:
            agreement_factor = min(1.0, max(0.35, float(agreement)))
        except Exception:
            agreement_factor = 1.0

    adjustment = average_score * confidence * headline_factor * agreement_factor * float(max_adjustment)
    adjustment = float(np.clip(adjustment, -abs(max_adjustment), abs(max_adjustment)))

    return {
        "available": True,
        "adjustment": adjustment,
        "average_score": average_score,
        "confidence": confidence,
        "headline_count": headline_count,
        "headline_factor": headline_factor,
        "agreement": agreement,
        "agreement_factor": agreement_factor,
        "max_adjustment": float(max_adjustment),
        "reason": (
            f"Sentiment score {average_score:+.2f}, confidence {confidence:.1%}, "
            f"{headline_count} headlines, max adjustment {float(max_adjustment):.1%}."
        ),
    }


def fuse_prediction_with_sentiment(
    base_prediction: dict[str, Any],
    sentiment_summary: dict[str, Any] | None,
    max_adjustment: float = 0.08,
) -> dict[str, Any]:
    """
    Blend the model's next-period up probability with recent-news sentiment.

    This is not a replacement for historical training with sentiment features. It is
    a transparent post-model overlay so the dashboard can show how recent news
    changes the risk/signal interpretation.
    """
    base_up_probability = float(base_prediction.get("up_probability", 0.5) or 0.5)
    adj = sentiment_adjustment(sentiment_summary, max_adjustment=max_adjustment)

    adjusted_up_probability = _clip_probability(base_up_probability + adj["adjustment"])

    signal = _signal_from_probability(adjusted_up_probability)
    base_signal = base_prediction.get("signal", _signal_from_probability(base_up_probability))
    confidence_label = _confidence_label(adjusted_up_probability, adj["adjustment"], adj["confidence"])

    if not adj["available"]:
        explanation = "No sentiment overlay applied because no usable recent-news sentiment was available."
    elif abs(adj["adjustment"]) < 0.005:
        explanation = "Recent-news sentiment had a minimal effect on the model probability."
    elif adj["adjustment"] > 0:
        explanation = "Recent-news sentiment tilted the signal upward."
    else:
        explanation = "Recent-news sentiment tilted the signal downward."

    return {
        "available": adj["available"],
        "base_up_probability": base_up_probability,
        "adjusted_up_probability": adjusted_up_probability,
        "base_signal": base_signal,
        "signal": signal,
        "adjustment": adj["adjustment"],
        "adjustment_pct_points": adj["adjustment"] * 100,
        "confidence_label": confidence_label,
        "sentiment_score": adj["average_score"],
        "sentiment_confidence": adj["confidence"],
        "headline_count": adj["headline_count"],
        "agreement": adj["agreement"],
        "max_adjustment": adj.get("max_adjustment", float(max_adjustment)),
        "explanation": explanation,
        "reason": adj["reason"],
    }


def build_signal_components_frame(fusion_result: dict[str, Any] | None) -> pd.DataFrame:
    """Return a compact table for the Prediction tab."""
    if not fusion_result:
        return pd.DataFrame()

    rows = [
        {
            "component": "Base model probability",
            "value": f"{fusion_result['base_up_probability']:.1%}",
            "interpretation": f"Base model signal: {fusion_result['base_signal']}",
        },
        {
            "component": "Sentiment adjustment",
            "value": f"{fusion_result['adjustment_pct_points']:+.2f} pp",
            "interpretation": fusion_result["explanation"],
        },
        {
            "component": "Sentiment score",
            "value": f"{fusion_result['sentiment_score']:+.2f}",
            "interpretation": f"{fusion_result['headline_count']} recent headlines, confidence {fusion_result['sentiment_confidence']:.1%}",
        },
        {
            "component": "Adjusted probability",
            "value": f"{fusion_result['adjusted_up_probability']:.1%}",
            "interpretation": f"Final sentiment-aware signal: {fusion_result['signal']}",
        },
    ]
    if fusion_result.get("agreement") is not None:
        rows.append(
            {
                "component": "Model agreement",
                "value": f"{fusion_result['agreement']:.1%}",
                "interpretation": "Agreement among sentiment models in the ensemble.",
            }
        )
    return pd.DataFrame(rows)
