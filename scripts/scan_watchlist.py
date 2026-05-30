from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DEFAULT_WATCHLIST
from src.watchlist import scan_watchlist, summarize_watchlist_scan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local Meroq watchlist intelligence scan.")
    parser.add_argument("--tickers", default=",".join(DEFAULT_WATCHLIST), help="Comma-separated tickers.")
    parser.add_argument("--period", default="5y", help="History period passed to yfinance.")
    parser.add_argument("--interval", default="1d", choices=["1d", "1wk"], help="Price interval.")
    parser.add_argument("--news-source", default="all_configured", help="News source key.")
    parser.add_argument("--engine", default="lightweight", help="Sentiment engine key.")
    parser.add_argument("--max-news", type=int, default=10, help="Max headlines per ticker.")
    parser.add_argument("--days-back", type=int, default=7, help="News lookback window.")
    parser.add_argument("--no-sentiment", action="store_true", help="Disable news sentiment.")
    parser.add_argument("--no-risk", action="store_true", help="Disable risk simulation.")
    parser.add_argument("--output", default="", help="Optional CSV output path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tickers = [x.strip().upper() for x in args.tickers.split(",") if x.strip()]
    df = scan_watchlist(
        tickers=tickers,
        period=args.period,
        interval=args.interval,
        news_source=args.news_source,
        sentiment_engine=args.engine,
        max_news_items=args.max_news,
        days_back=args.days_back,
        include_sentiment=not args.no_sentiment,
        include_risk=not args.no_risk,
        risk_horizon=30,
        risk_paths=500,
    )
    print("Summary:", summarize_watchlist_scan(df))
    if not df.empty:
        show_cols = [
            "ticker",
            "status",
            "latest_close",
            "base_signal",
            "base_up_probability",
            "sentiment_label",
            "final_signal",
            "final_up_probability",
            "risk_label",
            "meroq_score",
            "error",
        ]
        show_cols = [c for c in show_cols if c in df.columns]
        print(df[show_cols].to_string(index=False))
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
        print(f"Saved: {out}")


if __name__ == "__main__":
    main()
