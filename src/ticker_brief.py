from __future__ import annotations

from typing import Any

import numpy as np


Tone = str


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if np.isfinite(number) else default


def _grade_rank(value: Any) -> int:
    return {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}.get(str(value or "").upper(), 0)


def _stance_label(probability: float | None, grade: str, risk_loss: float | None, sentiment_score: float | None) -> tuple[str, Tone]:
    rank = _grade_rank(grade)
    if probability is None:
        return "Insufficient evidence", "neutral"

    elevated_risk = risk_loss is not None and risk_loss >= 0.45
    negative_sentiment = sentiment_score is not None and sentiment_score <= -0.2

    if probability >= 0.58 and rank >= 4 and not elevated_risk:
        return "Constructive research setup", "positive"
    if probability <= 0.44 or rank <= 2 or elevated_risk or negative_sentiment:
        return "Cautionary review", "negative"
    if probability >= 0.54 or rank >= 4:
        return "Constructive but needs confirmation", "warning"
    return "Balanced / watch", "warning"


def _conviction_label(probability: float | None, grade: str, headline_count: int, risk_available: bool) -> tuple[str, Tone]:
    if probability is None:
        return "Unknown conviction", "neutral"
    distance = abs(probability - 0.5)
    rank = _grade_rank(grade)
    if distance >= 0.14 and rank >= 4 and headline_count >= 3 and risk_available:
        return "Higher conviction", "positive"
    if distance >= 0.07 and rank >= 3:
        return "Moderate conviction", "warning"
    return "Low conviction", "neutral"


def _primary_driver(
    probability: float | None,
    base_probability: float | None,
    sentiment_adjustment: float | None,
    risk_loss: float | None,
    grade: str,
) -> str:
    if probability is None:
        return "No reliable driver yet"
    if risk_loss is not None and risk_loss >= 0.45:
        return "Risk lens is the main constraint"
    if sentiment_adjustment is not None and abs(sentiment_adjustment) >= 3.0:
        return "Recent news meaningfully changed the read"
    if base_probability is not None and abs(base_probability - 0.5) >= 0.1:
        return "Model signal is the main driver"
    if _grade_rank(grade) >= 4:
        return "Grade quality is carrying the setup"
    return "No single dominant driver"


def _evidence_quality(headline_count: int, risk_available: bool, roc_auc: float | None, train_rows: int) -> tuple[str, Tone]:
    model_ok = roc_auc is None or roc_auc >= 0.52
    if headline_count >= 5 and risk_available and model_ok and train_rows >= 120:
        return "Broad evidence", "positive"
    if headline_count >= 1 or risk_available or train_rows >= 120:
        return "Partial evidence", "warning"
    return "Thin evidence", "negative"


def _risk_label(risk_loss: float | None, risk_positive: float | None, risk_label: str | None) -> tuple[str, Tone]:
    if risk_loss is None and risk_positive is None:
        return "Risk lens unavailable", "neutral"
    if risk_loss is not None and risk_loss >= 0.45:
        return "Elevated downside risk", "negative"
    if risk_positive is not None and risk_positive >= 0.58:
        return "Constructive risk skew", "positive"
    return risk_label or "Balanced risk profile", "warning"


def _sentiment_label(sentiment_label: str | None, sentiment_score: float | None, headline_count: int) -> tuple[str, Tone]:
    if headline_count <= 0:
        return "No recent sentiment evidence", "neutral"
    if sentiment_score is not None and sentiment_score >= 0.2:
        return "Constructive news tone", "positive"
    if sentiment_score is not None and sentiment_score <= -0.2:
        return "Cautionary news tone", "negative"
    return sentiment_label or "Mixed / neutral news tone", "warning"


def _key_point(title: str, value: str, note: str, tone: Tone = "neutral") -> dict[str, str]:
    return {"title": title, "value": value, "note": note, "tone": tone}


def _format_pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def build_ticker_brief(summary: dict[str, Any], risk_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a compact analyst-style research brief from a ticker analysis summary.

    The brief deliberately avoids buy/sell wording. It is designed to help users
    decide what to inspect next: model signal, risk, sentiment, and evidence quality.
    """
    risk_summary = risk_summary or {}
    ticker = str(summary.get("ticker") or "This ticker")
    probability = _safe_float(summary.get("final_up_probability"), _safe_float(summary.get("base_up_probability")))
    base_probability = _safe_float(summary.get("base_up_probability"))
    sentiment_adjustment = _safe_float(summary.get("sentiment_adjustment_pct_points"))
    sentiment_score = _safe_float(summary.get("news_sentiment_score"))
    headline_count = int(_safe_float(summary.get("headlines_analyzed"), 0) or 0)
    risk_loss = _safe_float(summary.get("risk_probability_loss_gt_5pct"), _safe_float(risk_summary.get("probability_loss_gt_5pct")))
    risk_positive = _safe_float(summary.get("risk_probability_positive_return"), _safe_float(risk_summary.get("probability_positive_return")))
    grade = str(summary.get("meroq_grade") or "N/A")
    roc_auc = _safe_float(summary.get("simple_split_roc_auc"))
    train_rows = int(_safe_float(summary.get("train_rows"), 0) or 0)
    risk_available = risk_loss is not None or risk_positive is not None

    stance, stance_tone = _stance_label(probability, grade, risk_loss, sentiment_score)
    conviction, conviction_tone = _conviction_label(probability, grade, headline_count, risk_available)
    evidence_quality, evidence_tone = _evidence_quality(headline_count, risk_available, roc_auc, train_rows)
    risk_read, risk_tone = _risk_label(risk_loss, risk_positive, str(summary.get("risk_label") or "") or None)
    sentiment_read, sentiment_tone = _sentiment_label(str(summary.get("news_sentiment_label") or "") or None, sentiment_score, headline_count)
    primary_driver = _primary_driver(probability, base_probability, sentiment_adjustment, risk_loss, grade)

    key_points = [
        _key_point(
            "Model signal",
            _format_pct(probability),
            f"Final up-probability after the configured sentiment overlay. Base model was {_format_pct(base_probability)}.",
            "positive" if probability is not None and probability >= 0.56 else "negative" if probability is not None and probability <= 0.44 else "warning",
        ),
        _key_point("Meroq Grade", grade, str(summary.get("grade_summary") or "Composite grade from signal, risk, sentiment, momentum, confidence, and data quality."), stance_tone),
        _key_point("Risk read", risk_read, f"Probability of >5% downside: {_format_pct(risk_loss)}.", risk_tone),
        _key_point("News read", sentiment_read, f"Headlines analyzed: {headline_count}.", sentiment_tone),
        _key_point("Evidence quality", evidence_quality, f"Training rows: {train_rows}. Risk lens: {'available' if risk_available else 'skipped'}.", evidence_tone),
    ]

    watch_items: list[str] = []
    if risk_loss is not None and risk_loss >= 0.45:
        watch_items.append("Review whether downside risk is too high for the ticker's role in a portfolio.")
    if headline_count == 0:
        watch_items.append("Run with recent news enabled or verify the ticker manually because sentiment evidence is thin.")
    elif sentiment_score is not None and sentiment_score <= -0.2:
        watch_items.append("Inspect cautionary headlines before trusting the directional model.")
    if probability is not None and abs(probability - 0.5) < 0.07:
        watch_items.append("Treat the forecast as low-conviction because the probability is close to balanced.")
    if _grade_rank(grade) <= 2:
        watch_items.append("Check which component grade is pulling the setup down before deeper research.")
    if not watch_items:
        watch_items.append("Validate the setup against recent filings, sector context, and your own thesis before acting.")

    research_checks = [
        "Open the strongest positive and cautionary headlines to confirm target relevance.",
        "Compare the component grades against peer tickers instead of reading the score alone.",
        "Check whether the risk simulation horizon matches the decision timeframe.",
    ]
    if risk_loss is not None and risk_loss >= 0.45:
        research_checks.insert(0, "Stress-test position sizing or portfolio exposure before treating this as a candidate.")
    if headline_count < 3:
        research_checks.insert(0, "Add more source-backed evidence before relying on the sentiment overlay.")

    brief_sentence = (
        f"{ticker} is a {stance.lower()} with {conviction.lower()}. "
        f"{primary_driver}. Evidence quality is {evidence_quality.lower()}."
    )

    return {
        "ticker": ticker,
        "stance_label": stance,
        "stance_tone": stance_tone,
        "conviction_label": conviction,
        "conviction_tone": conviction_tone,
        "primary_driver": primary_driver,
        "evidence_quality": evidence_quality,
        "evidence_tone": evidence_tone,
        "risk_read": risk_read,
        "risk_tone": risk_tone,
        "sentiment_read": sentiment_read,
        "sentiment_tone": sentiment_tone,
        "brief_sentence": brief_sentence,
        "key_points": key_points,
        "watch_items": watch_items[:4],
        "research_checks": research_checks[:4],
    }
