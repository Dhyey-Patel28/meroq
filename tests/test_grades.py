from __future__ import annotations

from src.grades import build_grade_bundle, grade_label, score_to_grade


def test_score_to_grade_uses_research_thresholds() -> None:
    assert score_to_grade(83) == "A"
    assert score_to_grade(72) == "B"
    assert score_to_grade(58) == "C"
    assert score_to_grade(45) == "D"
    assert score_to_grade(25) == "F"


def test_grade_bundle_flags_risk_drag() -> None:
    bundle = build_grade_bundle(
        meroq_score=39,
        final_up_probability=0.46,
        sentiment_score=-0.35,
        headline_count=8,
        risk_loss_gt_5pct=0.55,
        risk_positive_probability=0.35,
        close_sma20_ratio=-0.03,
        rsi_14=72,
        model_roc_auc=0.49,
        model_accuracy=0.48,
    )

    assert bundle["meroq_grade"] == "F"
    assert bundle["risk_grade"] == "F"
    assert "risk" in bundle["grade_summary"].lower()


def test_grade_labels_are_not_buy_sell_language() -> None:
    label = grade_label("B").lower()
    assert "buy" not in label
    assert "sell" not in label
    assert "candidate" in label
