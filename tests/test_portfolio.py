from __future__ import annotations

import pandas as pd

from src.portfolio import build_portfolio_view, parse_portfolio_weights


def test_parse_portfolio_weights_equal_weight() -> None:
    weights = parse_portfolio_weights(["AAPL", "MSFT", "SPY"], "")
    assert list(weights["ticker"]) == ["AAPL", "MSFT", "SPY"]
    assert round(float(weights["weight"].sum()), 6) == 1.0
    assert all(round(float(w), 6) == round(1 / 3, 6) for w in weights["weight"])


def test_parse_portfolio_weights_custom_percentages() -> None:
    weights = parse_portfolio_weights(["AAPL", "MSFT", "SPY"], "AAPL:50,MSFT:30,SPY:20")
    by_ticker = dict(zip(weights["ticker"], weights["weight"]))
    assert round(by_ticker["AAPL"], 4) == 0.5
    assert round(by_ticker["MSFT"], 4) == 0.3
    assert round(by_ticker["SPY"], 4) == 0.2


def test_build_portfolio_view_summary() -> None:
    scan = pd.DataFrame(
        [
            {
                "ticker": "AAPL",
                "status": "ok",
                "latest_close": 100,
                "return_1d": 0.01,
                "base_up_probability": 0.55,
                "final_up_probability": 0.56,
                "sentiment_score": 0.2,
                "risk_loss_gt_5pct": 0.1,
                "risk_positive_probability": 0.6,
                "risk_median_return": 0.02,
                "meroq_score": 60,
                "model_roc_auc": 0.52,
                "final_signal": "Neutral",
                "sentiment_label": "Positive",
                "risk_label": "Balanced risk profile",
            },
            {
                "ticker": "MSFT",
                "status": "ok",
                "latest_close": 200,
                "return_1d": -0.01,
                "base_up_probability": 0.45,
                "final_up_probability": 0.44,
                "sentiment_score": -0.1,
                "risk_loss_gt_5pct": 0.2,
                "risk_positive_probability": 0.4,
                "risk_median_return": -0.01,
                "meroq_score": 45,
                "model_roc_auc": 0.49,
                "final_signal": "Neutral",
                "sentiment_label": "Negative",
                "risk_label": "High downside risk",
            },
        ]
    )
    weights = parse_portfolio_weights(["AAPL", "MSFT"], "AAPL:75,MSFT:25")
    holdings, summary = build_portfolio_view(scan, weights)
    assert len(holdings) == 2
    assert round(float(holdings["weight"].sum()), 6) == 1.0
    assert round(summary["weighted_meroq_score"], 2) == 56.25
    assert summary["holding_count"] == 2


def test_build_portfolio_view_adds_command_center_insights() -> None:
    scan = pd.DataFrame(
        [
            {
                "ticker": "AAPL",
                "status": "ok",
                "latest_close": 100,
                "return_1d": 0.01,
                "final_up_probability": 0.62,
                "sentiment_score": 0.2,
                "risk_loss_gt_5pct": 0.12,
                "risk_positive_probability": 0.65,
                "risk_median_return": 0.03,
                "meroq_score": 72,
                "meroq_grade": "B",
                "final_signal": "Bullish",
                "sentiment_label": "Positive",
                "risk_label": "Balanced risk profile",
            },
            {
                "ticker": "MARA",
                "status": "ok",
                "latest_close": 20,
                "return_1d": -0.02,
                "final_up_probability": 0.38,
                "sentiment_score": -0.25,
                "risk_loss_gt_5pct": 0.52,
                "risk_positive_probability": 0.31,
                "risk_median_return": -0.04,
                "meroq_score": 31,
                "meroq_grade": "F",
                "final_signal": "Bearish",
                "sentiment_label": "Cautionary",
                "risk_label": "High downside risk",
            },
            {
                "ticker": "MSFT",
                "status": "ok",
                "latest_close": 220,
                "return_1d": 0.0,
                "final_up_probability": 0.55,
                "sentiment_score": 0.05,
                "risk_loss_gt_5pct": 0.16,
                "risk_positive_probability": 0.55,
                "risk_median_return": 0.01,
                "meroq_score": 58,
                "meroq_grade": "C",
                "final_signal": "Neutral",
                "sentiment_label": "Neutral",
                "risk_label": "Balanced risk profile",
            },
        ]
    )
    weights = parse_portfolio_weights(["AAPL", "MARA", "MSFT"], "AAPL:50,MARA:30,MSFT:20")
    holdings, summary = build_portfolio_view(scan, weights)

    assert "exposure_note" in holdings.columns
    assert "downside_contribution_share" in holdings.columns
    assert summary["largest_position_ticker"] == "AAPL"
    assert summary["largest_position_weight"] == 0.5
    assert summary["concentration_label"] == "Concentrated"
    assert summary["top_risk_contributors"][0]["ticker"] == "MARA"
    assert summary["weakest_holdings"][0]["ticker"] == "MARA"
    assert any(row["grade"] == "F" and row["weight"] > 0 for row in summary["grade_distribution"])
    assert any(alert["title"] == "Top downside driver" for alert in summary["portfolio_alerts"])


def test_build_portfolio_view_adds_scenario_lab_fields() -> None:
    scan = pd.DataFrame(
        [
            {
                "ticker": "AAPL",
                "status": "ok",
                "latest_close": 100,
                "return_1d": 0.01,
                "final_up_probability": 0.64,
                "sentiment_score": 0.3,
                "risk_loss_gt_5pct": 0.10,
                "risk_positive_probability": 0.65,
                "risk_median_return": 0.03,
                "meroq_score": 76,
                "meroq_grade": "B",
                "final_signal": "Bullish",
                "sentiment_label": "Positive",
                "risk_label": "Balanced risk profile",
            },
            {
                "ticker": "MARA",
                "status": "ok",
                "latest_close": 20,
                "return_1d": -0.02,
                "final_up_probability": 0.36,
                "sentiment_score": -0.35,
                "risk_loss_gt_5pct": 0.55,
                "risk_positive_probability": 0.3,
                "risk_median_return": -0.04,
                "meroq_score": 28,
                "meroq_grade": "F",
                "final_signal": "Bearish",
                "sentiment_label": "Cautionary",
                "risk_label": "High downside risk",
            },
            {
                "ticker": "MSFT",
                "status": "ok",
                "latest_close": 220,
                "return_1d": 0.0,
                "final_up_probability": 0.56,
                "sentiment_score": 0.08,
                "risk_loss_gt_5pct": 0.16,
                "risk_positive_probability": 0.55,
                "risk_median_return": 0.01,
                "meroq_score": 61,
                "meroq_grade": "C",
                "final_signal": "Neutral",
                "sentiment_label": "Neutral",
                "risk_label": "Balanced risk profile",
            },
        ]
    )
    weights = parse_portfolio_weights(["AAPL", "MARA", "MSFT"], "AAPL:25,MARA:55,MSFT:20")
    holdings, summary = build_portfolio_view(scan, weights)

    assert "research_weight" in holdings.columns
    assert "research_weight_delta" in holdings.columns
    assert "allocation_review" in holdings.columns
    assert round(float(holdings["research_weight"].sum()), 6) == 1.0

    scenarios = summary["scenario_comparison"]
    assert [row["scenario_key"] for row in scenarios] == ["current", "equal_weight", "research_weighted"]
    research = summary["research_weighted_scenario"]
    assert research["scenario_key"] == "research_weighted"
    assert research["weighted_downside_probability"] < summary["weighted_downside_probability"]
    assert research["score_delta"] > 0

    mara = holdings.loc[holdings["ticker"] == "MARA"].iloc[0]
    assert float(mara["research_weight_delta"]) < 0
    assert "trims" in str(mara["allocation_review"]).lower()
