from __future__ import annotations

import asyncio
from typing import Any

import httpx

from api.main import create_app


async def _async_request(method: str, path: str, **kwargs: Any) -> httpx.Response:
    """Call the ASGI app directly without FastAPI/Starlette TestClient.

    Using HTTPX's ASGITransport avoids the Starlette TestClient deprecation
    warning while keeping these tests deterministic and network-free.
    """
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, path, **kwargs)


def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
    return asyncio.run(_async_request(method, path, **kwargs))


def test_health_endpoint() -> None:
    response = _request("GET", "/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "Meroq API"


def test_root_endpoint_points_to_docs() -> None:
    response = _request("GET", "/")
    assert response.status_code == 200
    body = response.json()
    assert body["docs"] == "/docs"
    assert body["health"] == "/health"


def test_metadata_endpoint_has_defaults() -> None:
    response = _request("GET", "/metadata")
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

    response = _request(
        "POST",
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
