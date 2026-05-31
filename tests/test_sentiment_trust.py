from __future__ import annotations

import pandas as pd

from src.news_sentiment import analyze_news_sentiment, summarize_sentiment


def test_buy_instead_headline_is_cautionary_for_target() -> None:
    df = pd.DataFrame(
        [
            {
                "ticker": "PLAY",
                "company_name": "Dave & Buster's Entertainment",
                "company_aliases": "Dave & Buster's Entertainment, Dave and Busters, PLAY",
                "relevance_score": 7.0,
                "title": "3 Reasons PLAY is Risky and 1 Stock to Buy Instead",
                "summary": "",
                "publisher": "StockStory",
                "published_at": "2026-04-08T18:13:47Z",
                "url": "https://example.com/play-risky",
                "source": "unit-test",
            }
        ]
    )

    scored = analyze_news_sentiment(df, engine="lightweight")
    row = scored.iloc[0]

    assert row["sentiment_label"] == "Negative"
    assert row["target_sentiment_label"] == "Cautionary"
    assert row["sentiment_score"] < 0
    assert "buy-alternative-framing" in row["reason_tags"]
    assert "risky" in row["sentiment_explanation"].lower()


def test_low_relevance_headline_is_not_forced_directional() -> None:
    df = pd.DataFrame(
        [
            {
                "ticker": "PLAY",
                "company_name": "Dave & Buster's Entertainment",
                "company_aliases": "Dave & Buster's Entertainment, Dave and Busters",
                "relevance_score": 1.0,
                "title": "PlayStation fans celebrate a new game launch",
                "summary": "",
                "publisher": "Example",
                "published_at": "2026-04-08T18:13:47Z",
                "url": "https://example.com/playstation",
                "source": "unit-test",
            }
        ]
    )

    scored = analyze_news_sentiment(df, engine="lightweight")
    row = scored.iloc[0]

    assert row["sentiment_label"] == "Neutral"
    assert row["target_sentiment_label"] == "Irrelevant"
    assert row["target_relevance_label"] == "Low"


def test_summary_uses_target_display_label() -> None:
    df = pd.DataFrame(
        [
            {
                "ticker": "PLAY",
                "company_name": "Dave & Buster's Entertainment",
                "company_aliases": "Dave & Buster's Entertainment, Dave and Busters, PLAY",
                "relevance_score": 7.0,
                "title": "3 Reasons PLAY is Risky and 1 Stock to Buy Instead",
                "summary": "",
                "publisher": "StockStory",
                "published_at": "2026-04-08T18:13:47Z",
                "url": "https://example.com/play-risky",
                "source": "unit-test",
            }
        ]
    )

    summary = summarize_sentiment(analyze_news_sentiment(df, engine="lightweight"))

    assert summary["overall_label"] == "Negative"
    assert summary["display_label"] == "Cautionary"
    assert summary["cautionary_count"] == 1
