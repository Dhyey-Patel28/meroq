from __future__ import annotations

import math
from typing import Any


def clamp_score(value: float | int | None, default: float = 50.0) -> float:
    """Clamp a score to Meroq's 0-100 research-grade scale."""
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        number = default
    if not math.isfinite(number):
        number = default
    return round(max(0.0, min(100.0, number)), 2)


def score_to_grade(score: float | int | None) -> str:
    """Convert a 0-100 score into a compact research grade.

    The thresholds are intentionally calibrated for Meroq's local research score,
    not institutional buy/sell recommendations. A grade is an attention label,
    not financial advice.
    """
    s = clamp_score(score)
    if s >= 82:
        return "A"
    if s >= 70:
        return "B"
    if s >= 56:
        return "C"
    if s >= 42:
        return "D"
    return "F"


def grade_tone(grade: str) -> str:
    grade = str(grade).upper().strip()
    if grade in {"A", "B"}:
        return "positive"
    if grade == "C":
        return "warning"
    if grade in {"D", "F"}:
        return "negative"
    return "neutral"


def grade_label(grade: str) -> str:
    labels = {
        "A": "A · strong research candidate",
        "B": "B · constructive candidate",
        "C": "C · balanced / watch",
        "D": "D · caution",
        "F": "F · weak / avoid until improved",
    }
    return labels.get(str(grade).upper(), "Unrated")


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return number


def momentum_component(close_sma20_ratio: Any = None, rsi_14: Any = None) -> float:
    ratio = _safe_float(close_sma20_ratio, 0.0) or 0.0
    rsi = _safe_float(rsi_14, 50.0) or 50.0
    score = 50.0 + ratio * 260.0
    if 45 <= rsi <= 65:
        score += 8.0
    elif 35 <= rsi < 45 or 65 < rsi <= 75:
        score += 2.0
    elif rsi > 80:
        score -= 8.0
    elif rsi < 25:
        score -= 8.0
    return clamp_score(score)


def risk_component(risk_loss_gt_5pct: Any = None, risk_positive_probability: Any = None) -> float:
    loss = _safe_float(risk_loss_gt_5pct, None)
    positive = _safe_float(risk_positive_probability, None)
    if loss is None and positive is None:
        return 50.0
    score = 62.0
    if loss is not None:
        score -= loss * 105.0
    if positive is not None:
        score += (positive - 0.5) * 42.0
    return clamp_score(score)


def sentiment_component(sentiment_score: Any = None, headline_count: Any = None) -> float:
    sentiment = _safe_float(sentiment_score, 0.0) or 0.0
    headlines = int(_safe_float(headline_count, 0.0) or 0.0)
    score = 50.0 + sentiment * 44.0
    if headlines == 0:
        score -= 5.0
    elif headlines >= 8:
        score += 3.0
    return clamp_score(score)


def model_confidence_component(model_roc_auc: Any = None, model_accuracy: Any = None, final_up_probability: Any = None) -> float:
    roc_auc = _safe_float(model_roc_auc, None)
    accuracy = _safe_float(model_accuracy, None)
    probability = _safe_float(final_up_probability, 0.5) or 0.5
    score = 45.0 + abs(probability - 0.5) * 85.0
    if roc_auc is not None:
        score += (roc_auc - 0.5) * 150.0
    elif accuracy is not None:
        score += (accuracy - 0.5) * 100.0
    return clamp_score(score)


def data_quality_component(status: Any = "ok", headline_count: Any = None, model_roc_auc: Any = None) -> float:
    if str(status).lower() == "failed":
        return 0.0
    score = 78.0
    headlines = int(_safe_float(headline_count, 0.0) or 0.0)
    if headlines == 0:
        score -= 6.0
    if _safe_float(model_roc_auc, None) is None:
        score -= 4.0
    return clamp_score(score)


def build_grade_bundle(
    *,
    meroq_score: Any = None,
    final_up_probability: Any = None,
    sentiment_score: Any = None,
    headline_count: Any = None,
    risk_loss_gt_5pct: Any = None,
    risk_positive_probability: Any = None,
    close_sma20_ratio: Any = None,
    rsi_14: Any = None,
    model_roc_auc: Any = None,
    model_accuracy: Any = None,
    status: Any = "ok",
) -> dict[str, Any]:
    """Build overall and component grades for a ticker.

    These grades are designed for product UX: they summarize what deserves
    attention. They are not buy/sell recommendations.
    """
    overall_score = clamp_score(meroq_score)
    overall_grade = score_to_grade(overall_score)
    momentum_score = momentum_component(close_sma20_ratio, rsi_14)
    risk_score = risk_component(risk_loss_gt_5pct, risk_positive_probability)
    sentiment_grade_score = sentiment_component(sentiment_score, headline_count)
    confidence_score = model_confidence_component(model_roc_auc, model_accuracy, final_up_probability)
    quality_score = data_quality_component(status, headline_count, model_roc_auc)

    return {
        "meroq_grade": overall_grade,
        "meroq_grade_label": grade_label(overall_grade),
        "meroq_grade_tone": grade_tone(overall_grade),
        "momentum_score": momentum_score,
        "momentum_grade": score_to_grade(momentum_score),
        "risk_score": risk_score,
        "risk_grade": score_to_grade(risk_score),
        "sentiment_grade_score": sentiment_grade_score,
        "sentiment_grade": score_to_grade(sentiment_grade_score),
        "model_confidence_score": confidence_score,
        "model_confidence_grade": score_to_grade(confidence_score),
        "data_quality_score": quality_score,
        "data_quality_grade": score_to_grade(quality_score),
        "grade_summary": grade_summary(overall_grade, risk_score, sentiment_grade_score, confidence_score),
    }


def grade_summary(overall_grade: str, risk_score: float, sentiment_score: float, confidence_score: float) -> str:
    parts: list[str] = [grade_label(overall_grade)]
    if risk_score < 42:
        parts.append("risk is the main drag")
    elif risk_score >= 70:
        parts.append("risk profile supports the read")
    if sentiment_score < 42:
        parts.append("recent news tone is cautionary")
    elif sentiment_score >= 70:
        parts.append("recent news tone is supportive")
    if confidence_score < 45:
        parts.append("model confidence is limited")
    return "; ".join(parts) + "."
