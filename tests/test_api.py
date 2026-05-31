from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app


client = TestClient(create_app())


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "Meroq API"


def test_root_endpoint_points_to_docs() -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["docs"] == "/docs"
    assert body["health"] == "/health"


def test_metadata_endpoint_has_defaults() -> None:
    response = client.get("/metadata")
    assert response.status_code == 200
    body = response.json()
    assert "models" in body
    assert "default_watchlist" in body
    assert "AAPL" in body["default_watchlist"]


def test_portfolio_endpoint_uses_ticker_first_weight_parser(monkeypatch) -> None:
    import api.main as main_module

    def fake_scan_watchlist(**kwargs):
        import pandas as pd

        return pd.DataFrame(
            [
                {
                    "ticker": "AAPL",
                    "status": "ok",
                    "latest_close": 100,
                    "return_1d": 0.0,
                    "base_up_probability": 0.55,
                    "final_up_probability": 0.55,
                    "sentiment_score": 0.0,
                    "risk_loss_gt_5pct": 0.1,
                    "risk_positive_probability": 0.6,
                    "risk_median_return": 0.01,
                    "meroq_score": 60,
                    "final_signal": "Neutral",
                    "sentiment_label": "Neutral",
                    "risk_label": "Balanced risk profile",
                },
                {
                    "ticker": "MSFT",
                    "status": "ok",
                    "latest_close": 200,
                    "return_1d": 0.0,
                    "base_up_probability": 0.45,
                    "final_up_probability": 0.45,
                    "sentiment_score": 0.0,
                    "risk_loss_gt_5pct": 0.2,
                    "risk_positive_probability": 0.4,
                    "risk_median_return": -0.01,
                    "meroq_score": 40,
                    "final_signal": "Neutral",
                    "sentiment_label": "Neutral",
                    "risk_label": "High downside risk",
                },
            ]
        )

    monkeypatch.setattr(main_module, "scan_watchlist", fake_scan_watchlist)

    response = client.post(
        "/portfolio/analyze",
        json={
            "tickers": ["AAPL", "MSFT"],
            "weights": "AAPL:80,MSFT:20",
            "include_sentiment": False,
            "include_risk": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["holding_count"] == 2
    assert round(body["summary"]["weighted_meroq_score"], 2) == 56.0
