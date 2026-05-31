from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test a running local Meroq API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL.")
    parser.add_argument("--ticker", default="AAPL", help="Ticker to test.")
    parser.add_argument("--skip-analysis", action="store_true", help="Only test health/metadata.")
    return parser.parse_args()


def _print(title: str, payload: Any) -> None:
    print(f"\n{title}\n" + "-" * len(title))
    print(json.dumps(payload, indent=2, default=str)[:3000])


def main() -> None:
    args = parse_args()
    base = args.base_url.rstrip("/")

    health = requests.get(f"{base}/health", timeout=20)
    health.raise_for_status()
    _print("Health", health.json())

    meta = requests.get(f"{base}/metadata", timeout=20)
    meta.raise_for_status()
    metadata = meta.json()
    _print("Metadata", {"version": metadata.get("version"), "models": list(metadata.get("models", {}).keys())})

    if not args.skip_analysis:
        response = requests.post(
            f"{base}/analysis/ticker",
            json={
                "ticker": args.ticker,
                "period": "1y",
                "interval": "1d",
                "model_name": "xgboost",
                "include_news": False,
                "include_risk": False,
            },
            timeout=120,
        )
        response.raise_for_status()
        _print("Ticker analysis summary", response.json().get("summary", {}))

    print("\nAPI smoke test passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"API smoke test failed: {exc}", file=sys.stderr)
        raise
