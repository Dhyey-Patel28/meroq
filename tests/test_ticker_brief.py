from __future__ import annotations

from src.ticker_brief import build_ticker_brief


def test_ticker_brief_marks_constructive_research_setup() -> None:
    brief = build_ticker_brief(
        {
            "ticker": "NVDA",
            "final_up_probability": 0.64,
            "base_up_probability": 0.61,
            "sentiment_adjustment_pct_points": 3.2,
            "news_sentiment_score": 0.28,
            "news_sentiment_label": "Positive",
            "headlines_analyzed": 8,
            "risk_probability_loss_gt_5pct": 0.18,
            "risk_probability_positive_return": 0.64,
            "risk_label": "Constructive risk profile",
            "meroq_grade": "A",
            "grade_summary": "Strong research candidate.",
            "simple_split_roc_auc": 0.58,
            "train_rows": 600,
        }
    )

    assert brief["ticker"] == "NVDA"
    assert brief["stance_label"] == "Constructive research setup"
    assert brief["conviction_label"] == "Higher conviction"
    assert brief["evidence_quality"] == "Broad evidence"
    assert any(point["title"] == "News read" for point in brief["key_points"])
    assert "buy" not in brief["brief_sentence"].lower()


def test_ticker_brief_flags_risk_and_thin_evidence() -> None:
    brief = build_ticker_brief(
        {
            "ticker": "MARA",
            "final_up_probability": 0.52,
            "base_up_probability": 0.54,
            "news_sentiment_score": -0.1,
            "news_sentiment_label": "Mixed",
            "headlines_analyzed": 0,
            "risk_probability_loss_gt_5pct": 0.57,
            "risk_probability_positive_return": 0.41,
            "risk_label": "High downside risk",
            "meroq_grade": "D",
            "grade_summary": "Cautionary setup.",
            "simple_split_roc_auc": 0.5,
            "train_rows": 60,
        }
    )

    assert brief["stance_label"] == "Cautionary review"
    assert brief["risk_read"] == "Elevated downside risk"
    assert any("downside risk" in item.lower() for item in brief["watch_items"])
    assert any("sentiment evidence is thin" in item.lower() for item in brief["watch_items"])


def test_ticker_brief_handles_no_risk_or_news() -> None:
    brief = build_ticker_brief(
        {
            "ticker": "SPY",
            "final_up_probability": 0.51,
            "base_up_probability": 0.51,
            "headlines_analyzed": 0,
            "meroq_grade": "C",
            "train_rows": 220,
        }
    )

    assert brief["conviction_label"] == "Low conviction"
    assert brief["risk_read"] == "Risk lens unavailable"
    assert brief["sentiment_read"] == "No recent sentiment evidence"
    assert brief["evidence_quality"] == "Partial evidence"
