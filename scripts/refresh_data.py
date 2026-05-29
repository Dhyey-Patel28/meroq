from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import DEFAULT_WATCHLIST  # noqa: E402
from src.data_loader import fetch_price_data  # noqa: E402
from src.storage import is_price_data_fresh  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh Meroq market data with freshness checks.")
    parser.add_argument("--tickers", nargs="*", default=DEFAULT_WATCHLIST, help="Tickers to refresh.")
    parser.add_argument("--period", default="max", help="yfinance period, e.g. 5y, 10y, max.")
    parser.add_argument("--interval", default="1d", help="yfinance interval, e.g. 1d or 1wk.")
    parser.add_argument("--max-age-hours", type=float, default=18.0, help="Skip refresh if cached data is newer than this.")
    parser.add_argument("--force", action="store_true", help="Refresh even if local data is fresh.")
    parser.add_argument("--sleep", type=float, default=0.75, help="Seconds to sleep between requests.")
    args = parser.parse_args()

    print("Meroq market data refresh")
    print(f"Tickers: {', '.join(args.tickers)}")
    print(f"Period: {args.period}")
    print(f"Interval: {args.interval}")

    for ticker in args.tickers:
        try:
            if not args.force and is_price_data_fresh(ticker, args.interval, max_age_hours=args.max_age_hours):
                print(f"• {ticker}: skipped; local data is fresh")
                continue

            df = fetch_price_data(ticker=ticker, period=args.period, interval=args.interval, save_to_sqlite=True)
            start = df["Date"].min().date() if not df.empty else "n/a"
            end = df["Date"].max().date() if not df.empty else "n/a"
            print(f"✓ {ticker}: saved {len(df):,} rows ({start} → {end})")
        except Exception as exc:
            print(f"✗ {ticker}: {exc}")
        time.sleep(args.sleep)


if __name__ == "__main__":
    main()
