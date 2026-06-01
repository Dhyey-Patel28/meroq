from __future__ import annotations

import pandas as pd

from src.watchlist import enrich_watchlist_row, summarize_watchlist_scan


def test_enrich_watchlist_row_assigns_research_queue() -> None:
    row = enrich_watchlist_row(
        {
            "ticker": "NVDA",
            "status": "ok",
            "meroq_score": 82,
            "meroq_grade": "A",
            "final_up_probability": 0.64,
            "sentiment_score": 0.25,
            "sentiment_label": "Positive",
            "risk_label": "Balanced risk profile",
            "risk_loss_gt_5pct": 0.12,
            "headline_count": 8,
        }
    )

    assert row["watchlist_bucket"] == "Research queue"
    assert row["research_priority"] >= 80
    assert row["evidence_count"] == 8
    assert "NVDA" in row["scan_note"]


def test_enrich_watchlist_row_flags_risk_review_before_candidate() -> None:
    row = enrich_watchlist_row(
        {
            "ticker": "MARA",
            "status": "ok",
            "meroq_score": 74,
            "meroq_grade": "B",
            "final_up_probability": 0.61,
            "sentiment_score": -0.35,
            "sentiment_label": "Cautionary",
            "risk_label": "High downside risk",
            "risk_loss_gt_5pct": 0.55,
            "headline_count": 5,
        }
    )

    assert row["watchlist_bucket"] == "Risk review"
    assert row["research_priority"] < 74
    assert "review" in row["scan_note"].lower()


def test_summarize_watchlist_scan_adds_command_center_fields() -> None:
    rows = pd.DataFrame(
        [
            enrich_watchlist_row(
                {
                    "ticker": "NVDA",
                    "status": "ok",
                    "meroq_score": 84,
                    "meroq_grade": "A",
                    "final_up_probability": 0.66,
                    "sentiment_score": 0.25,
                    "sentiment_label": "Positive",
                    "risk_label": "Balanced risk profile",
                    "risk_loss_gt_5pct": 0.10,
                    "headline_count": 9,
                    "final_signal": "Bullish",
                }
            ),
            enrich_watchlist_row(
                {
                    "ticker": "MARA",
                    "status": "ok",
                    "meroq_score": 35,
                    "meroq_grade": "F",
                    "final_up_probability": 0.39,
                    "sentiment_score": -0.45,
                    "sentiment_label": "Cautionary",
                    "risk_label": "High downside risk",
                    "risk_loss_gt_5pct": 0.58,
                    "headline_count": 6,
                    "final_signal": "Bearish",
                }
            ),
            enrich_watchlist_row(
                {
                    "ticker": "BAD",
                    "status": "failed",
                    "error": "Unable to load data for BAD.",
                }
            ),
        ]
    )

    summary = summarize_watchlist_scan(rows)

    assert summary["ready_count"] == 2
    assert summary["issue_count"] == 1
    assert summary["research_queue_count"] == 1
    assert summary["risk_review_count"] == 1
    assert summary["best_candidate_ticker"] == "NVDA"
    assert summary["top_research_candidates"][0]["ticker"] == "NVDA"
    assert summary["risk_review"][0]["ticker"] == "MARA"
    assert any(alert["title"] == "Best research candidate" for alert in summary["scan_alerts"])
    assert any(row["grade"] == "A" for row in summary["grade_distribution"])
