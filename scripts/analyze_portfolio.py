from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.portfolio import build_portfolio_view, parse_portfolio_weights, portfolio_summary_sentence
from src.watchlist import scan_watchlist


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local Meroq portfolio risk/exposure scan.")
    parser.add_argument("--tickers", default="AAPL,MSFT,NVDA,SPY", help="Comma-separated symbols.")
    parser.add_argument("--weights", default="", help="Optional weights, e.g. AAPL:40,MSFT:30,SPY:30")
    parser.add_argument("--period", default="5y")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--source", default="all_configured")
    parser.add_argument("--engine", default="lightweight")
    parser.add_argument("--max-items", type=int, default=10)
    parser.add_argument("--days-back", type=int, default=14)
    args = parser.parse_args()

    tickers = [x.strip().upper() for x in args.tickers.split(",") if x.strip()]
    scan_df = scan_watchlist(
        tickers=tickers,
        period=args.period,
        interval=args.interval,
        news_source=args.source,
        sentiment_engine=args.engine,
        max_news_items=args.max_items,
        days_back=args.days_back,
        include_sentiment=True,
        include_risk=True,
        risk_paths=500,
    )
    weights = parse_portfolio_weights(tickers, args.weights)
    portfolio_df, summary = build_portfolio_view(scan_df, weights)

    print("Summary:", summary)
    print(portfolio_summary_sentence(summary))
    if not portfolio_df.empty:
        cols = [
            "ticker",
            "weight",
            "latest_close",
            "final_signal",
            "final_up_probability",
            "sentiment_label",
            "risk_label",
            "risk_loss_gt_5pct",
            "meroq_score",
        ]
        cols = [c for c in cols if c in portfolio_df.columns]
        print(portfolio_df[cols].to_string(index=False))
    else:
        print("No portfolio rows produced.")


if __name__ == "__main__":
    main()
