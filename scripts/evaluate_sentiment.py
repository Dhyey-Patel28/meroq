from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.sentiment_evaluation import SentimentEvaluationConfig, evaluate_from_path  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate target-aware headline sentiment against the local gold dataset.")
    parser.add_argument("--gold", default="data/sentiment_gold/financial_headlines_gold.csv", help="Path to labeled headline CSV.")
    parser.add_argument("--engine", default="lightweight", help="Sentiment engine to evaluate.")
    parser.add_argument("--output", default="", help="Optional CSV path for detailed scored rows.")
    parser.add_argument("--fail-under-accuracy", type=float, default=0.0, help="Exit non-zero if target accuracy is below this value.")
    parser.add_argument("--fail-under-cautionary-recall", type=float, default=0.0, help="Exit non-zero if cautionary recall is below this value.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metrics, details = evaluate_from_path(
        SentimentEvaluationConfig(gold_path=Path(args.gold), engine=args.engine)
    )

    print(json.dumps(metrics, indent=2))

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        details.to_csv(output_path, index=False)
        print(f"Wrote details to {output_path}")

    failed = False
    if args.fail_under_accuracy and metrics["target_accuracy"] < args.fail_under_accuracy:
        print(f"FAIL: target_accuracy {metrics['target_accuracy']:.3f} < {args.fail_under_accuracy:.3f}", file=sys.stderr)
        failed = True
    if args.fail_under_cautionary_recall and metrics["cautionary_recall"] < args.fail_under_cautionary_recall:
        print(
            f"FAIL: cautionary_recall {metrics['cautionary_recall']:.3f} < {args.fail_under_cautionary_recall:.3f}",
            file=sys.stderr,
        )
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
