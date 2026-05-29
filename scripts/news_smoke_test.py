from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.news_sentiment import analyze_news_sentiment, fetch_news_for_ticker, summarize_sentiment  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Quickly test Meroq news sources and sentiment scoring.")
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument("--source", default="all_configured", choices=["all_configured", "yfinance", "finnhub", "newsapi", "auto_free"])
    parser.add_argument("--engine", default="lightweight")
    parser.add_argument("--max-items", type=int, default=20)
    parser.add_argument("--force-refresh", action="store_true")
    args = parser.parse_args()

    news, meta = fetch_news_for_ticker(
        ticker=args.ticker,
        source=args.source,
        max_items=args.max_items,
        force_refresh=args.force_refresh,
    )
    scored = analyze_news_sentiment(news, engine=args.engine)
    summary = summarize_sentiment(scored)

    print("Meta:", meta)
    print("Summary:", summary)
    if not scored.empty:
        cols = [col for col in ["published_at", "source", "publisher", "label", "score", "title"] if col in scored.columns]
        print(scored[cols].head(args.max_items).to_string(index=False))


if __name__ == "__main__":
    main()
