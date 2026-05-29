from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.storage import database_file_summary, inspect_market_database, inspect_news_cache  # noqa: E402


def _print_frame(title: str, df) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    if df.empty:
        print("No rows.")
    else:
        print(df.to_string(index=False))


def main() -> None:
    _print_frame("Database files", database_file_summary())
    _print_frame("Market data inventory", inspect_market_database())
    _print_frame("News cache inventory", inspect_news_cache())


if __name__ == "__main__":
    main()
