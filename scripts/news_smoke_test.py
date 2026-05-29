from __future__ import annotations

import argparse

from src.news_sentiment import analyze_news_sentiment, fetch_news_for_ticker, summarize_sentiment


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test Meroq news and sentiment providers.")
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument("--source", default="all_configured")
    parser.add_argument("--engine", default="lightweight")
    parser.add_argument("--max-items", type=int, default=20)
    parser.add_argument("--days-back", type=int, default=14)
    args = parser.parse_args()

    news_df, meta = fetch_news_for_ticker(
        ticker=args.ticker,
        source=args.source,
        max_items=args.max_items,
        days_back=args.days_back,
    )
    print("News metadata:", meta)
    print(news_df[[c for c in ["published_at", "source", "publisher", "title"] if c in news_df.columns]].head(10))

    sentiment_df = analyze_news_sentiment(news_df, engine=args.engine)
    print("Sentiment summary:", summarize_sentiment(sentiment_df))
    print(sentiment_df[[c for c in ["source", "sentiment_label", "sentiment_score", "confidence", "title"] if c in sentiment_df.columns]].head(10))


if __name__ == "__main__":
    main()
