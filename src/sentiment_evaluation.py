from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd

from src.news_sentiment import analyze_news_sentiment

LABELS = ["Positive", "Cautionary", "Neutral", "Irrelevant", "Uncertain"]
RELEVANCE_LABELS = ["High", "Medium", "Low"]


@dataclass(frozen=True)
class SentimentEvaluationConfig:
    gold_path: Path = Path("data/sentiment_gold/financial_headlines_gold.csv")
    engine: str = "lightweight"


def _normalize_target_label(value: Any) -> str:
    text = str(value or "").strip()
    if text.lower() in {"negative", "caution", "cautionary", "bearish"}:
        return "Cautionary"
    if text.lower() in {"positive", "bullish"}:
        return "Positive"
    if text.lower() in {"irrelevant", "not relevant", "unrelated"}:
        return "Irrelevant"
    if text.lower() in {"uncertain", "mixed"}:
        return "Uncertain"
    return "Neutral"


def _macro_f1(y_true: list[str], y_pred: list[str], labels: list[str]) -> float:
    f1_values: list[float] = []
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t == label and p != label)
        if tp == 0 and fp == 0 and fn == 0:
            continue
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        f1_values.append(f1)
    return float(sum(f1_values) / len(f1_values)) if f1_values else 0.0


def _recall_for_label(y_true: list[str], y_pred: list[str], label: str) -> float:
    total = sum(1 for item in y_true if item == label)
    if total == 0:
        return 0.0
    hits = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t == label and p == label)
    return hits / total


def load_gold_dataset(path: str | Path) -> pd.DataFrame:
    gold_path = Path(path)
    if not gold_path.exists():
        raise FileNotFoundError(f"Gold sentiment dataset not found: {gold_path}")
    df = pd.read_csv(gold_path)
    required = {"ticker", "title", "expected_target_sentiment", "expected_relevance_label"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Gold sentiment dataset missing required columns: {missing}")
    return df


def evaluate_sentiment_gold(
    gold_df: pd.DataFrame,
    engine: str = "lightweight",
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Evaluate target-aware sentiment against a labeled local benchmark."""
    started = perf_counter()
    scored = analyze_news_sentiment(gold_df, engine=engine)
    elapsed = perf_counter() - started

    if scored.empty:
        raise ValueError("Sentiment scorer returned no rows for the gold dataset.")

    details = scored.copy()
    details["expected_target_sentiment"] = gold_df["expected_target_sentiment"].map(_normalize_target_label).values
    details["expected_relevance_label"] = gold_df["expected_relevance_label"].astype(str).str.strip().values
    details["predicted_target_sentiment"] = details.get("target_sentiment_label", details.get("sentiment_label", "Neutral")).map(_normalize_target_label)
    details["predicted_relevance_label"] = details.get("target_relevance_label", "Low").astype(str).str.strip()
    details["target_match"] = details["expected_target_sentiment"] == details["predicted_target_sentiment"]
    details["relevance_match"] = details["expected_relevance_label"] == details["predicted_relevance_label"]

    y_true = details["expected_target_sentiment"].tolist()
    y_pred = details["predicted_target_sentiment"].tolist()
    relevance_true = details["expected_relevance_label"].tolist()
    relevance_pred = details["predicted_relevance_label"].tolist()

    headline_count = int(len(details))
    target_accuracy = float(details["target_match"].mean()) if headline_count else 0.0
    relevance_accuracy = float(details["relevance_match"].mean()) if headline_count else 0.0
    macro_f1 = _macro_f1(y_true, y_pred, LABELS)
    relevance_macro_f1 = _macro_f1(relevance_true, relevance_pred, RELEVANCE_LABELS)
    cautionary_recall = _recall_for_label(y_true, y_pred, "Cautionary")
    positive_recall = _recall_for_label(y_true, y_pred, "Positive")
    irrelevant_recall = _recall_for_label(y_true, y_pred, "Irrelevant")

    metrics = {
        "engine": engine,
        "headline_count": headline_count,
        "target_accuracy": round(target_accuracy, 4),
        "target_macro_f1": round(macro_f1, 4),
        "relevance_accuracy": round(relevance_accuracy, 4),
        "relevance_macro_f1": round(relevance_macro_f1, 4),
        "cautionary_recall": round(cautionary_recall, 4),
        "positive_recall": round(positive_recall, 4),
        "irrelevant_recall": round(irrelevant_recall, 4),
        "average_latency_ms_per_headline": round((elapsed / max(1, headline_count)) * 1000, 2),
        "mismatch_count": int((~details["target_match"]).sum()),
        "relevance_mismatch_count": int((~details["relevance_match"]).sum()),
    }
    return metrics, details


def evaluate_from_path(config: SentimentEvaluationConfig) -> tuple[dict[str, Any], pd.DataFrame]:
    return evaluate_sentiment_gold(load_gold_dataset(config.gold_path), engine=config.engine)
