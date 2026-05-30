from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services import SingleTickerAnalysisRequest, run_single_ticker_analysis, single_ticker_summary_frame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a reusable Meroq single-ticker analysis without Streamlit.")
    parser.add_argument("--ticker", required=True, help="Ticker symbol, for example AAPL or PLAY.")
    parser.add_argument("--period", default="5y", help="yfinance period, for example 1y, 5y, 10y, max.")
    parser.add_argument("--interval", default="1d", help="yfinance interval, for example 1d or 1wk.")
    parser.add_argument("--model", default="xgboost", help="Model name, for example xgboost or random_forest.")
    parser.add_argument("--news-source", default="all_configured", help="News source: yfinance, finnhub, newsapi, all_configured.")
    parser.add_argument("--sentiment-engine", default="lightweight", help="Sentiment engine, for example lightweight or ensemble_finance.")
    parser.add_argument("--max-news", type=int, default=30, help="Maximum headlines to score.")
    parser.add_argument("--no-news", action="store_true", help="Skip news sentiment.")
    parser.add_argument("--no-risk", action="store_true", help="Skip Monte Carlo risk simulation.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary instead of a table.")
    parser.add_argument("--output", default="", help="Optional path to write JSON summary.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    request = SingleTickerAnalysisRequest(
        ticker=args.ticker,
        period=args.period,
        interval=args.interval,
        model_name=args.model,
        include_news=not args.no_news,
        include_risk=not args.no_risk,
        news_source=args.news_source,
        sentiment_engine=args.sentiment_engine,
        max_news_items=args.max_news,
    )
    result = run_single_ticker_analysis(request)
    summary = result["summary"]

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Wrote summary to {output_path}")

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        df = single_ticker_summary_frame(result)
        with __import__("pandas").option_context("display.max_columns", None, "display.width", 160):
            print(df.to_string(index=False))


if __name__ == "__main__":
    main()
