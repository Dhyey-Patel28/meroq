from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import DEFAULT_WATCHLIST
from src.news_sentiment import analyze_news_sentiment, fetch_news_for_ticker, summarize_sentiment
from src.sentiment_features import aggregate_daily_sentiment
from src.storage import save_daily_sentiment_features


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh cached daily sentiment features for one or more tickers.")
    parser.add_argument("--tickers", nargs="*", default=DEFAULT_WATCHLIST, help="Ticker symbols to refresh.")
    parser.add_argument("--source", default="all_configured", help="News source: yfinance, finnhub, newsapi, all_configured.")
    parser.add_argument("--engine", default="lightweight", help="Sentiment engine to use.")
    parser.add_argument("--max-items", type=int, default=50, help="Maximum headlines per ticker.")
    parser.add_argument("--days-back", type=int, default=30, help="Lookback window for API-backed news sources.")
    parser.add_argument("--force-refresh", action="store_true", help="Bypass local cache and request fresh news.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    for ticker in args.tickers:
        print(f"\nRefreshing sentiment features for {ticker.upper()}...")
        news_df, meta = fetch_news_for_ticker(
            ticker=ticker,
            source=args.source,
            max_items=args.max_items,
            days_back=args.days_back,
            use_cache=True,
            force_refresh=args.force_refresh,
        )
        sentiment_df = analyze_news_sentiment(news_df, engine=args.engine)
        summary = summarize_sentiment(sentiment_df)
        daily = aggregate_daily_sentiment(sentiment_df, ticker=ticker)
        save_daily_sentiment_features(
            daily,
            ticker=ticker,
            engine=args.engine,
            source_used=str(meta.get("source_used", args.source)),
        )
        print(
            {
                "ticker": ticker.upper(),
                "headlines": int(summary.get("headline_count", 0) or 0),
                "overall_label": summary.get("overall_label"),
                "daily_rows_saved": len(daily),
                "source_used": meta.get("source_used"),
            }
        )


if __name__ == "__main__":
    main()
