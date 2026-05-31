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
