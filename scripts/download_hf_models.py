from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.news_sentiment import HF_MODEL_IDS  # noqa: E402


def main() -> None:
    try:
        from transformers import pipeline
    except Exception as exc:
        raise SystemExit(
            "transformers is not installed. Run: python -m pip install -r requirements.txt"
        ) from exc

    for key, model_id in HF_MODEL_IDS.items():
        print(f"Downloading/loading {key}: {model_id}")
        pipeline("text-classification", model=model_id, tokenizer=model_id, truncation=True)
        print(f"✓ ready: {model_id}")


if __name__ == "__main__":
    main()
