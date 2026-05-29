from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import DEFAULT_WATCHLIST  # noqa: E402
from src.data_loader import fetch_price_data  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and save historical data for Meroq's default watchlist.")
    parser.add_argument("--period", default="max", help="yfinance period, e.g. 5y, 10y, max")
    parser.add_argument("--interval", default="1d", help="yfinance interval, e.g. 1d or 1wk")
    parser.add_argument(
        "--tickers",
        nargs="*",
        default=DEFAULT_WATCHLIST,
        help="Optional custom ticker list. Defaults to the 10-stock Meroq universe.",
    )
    parser.add_argument("--sleep", type=float, default=0.75, help="Seconds to sleep between downloads.")
    args = parser.parse_args()

    print("Meroq watchlist bootstrap")
    print(f"Period: {args.period}")
    print(f"Interval: {args.interval}")
    print(f"Tickers: {', '.join(args.tickers)}")

    for ticker in args.tickers:
        try:
            df = fetch_price_data(ticker=ticker, period=args.period, interval=args.interval, save_to_sqlite=True)
            start = df["Date"].min().date() if not df.empty else "n/a"
            end = df["Date"].max().date() if not df.empty else "n/a"
            print(f"✓ {ticker}: saved {len(df):,} rows ({start} → {end})")
        except Exception as exc:
            print(f"✗ {ticker}: {exc}")
        time.sleep(args.sleep)


if __name__ == "__main__":
    main()
