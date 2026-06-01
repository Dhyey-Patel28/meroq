from __future__ import annotations

from pathlib import Path

from src.sentiment_evaluation import SentimentEvaluationConfig, evaluate_from_path, load_gold_dataset

GOLD_PATH = Path("data/sentiment_gold/financial_headlines_gold.csv")


def test_gold_dataset_is_present_and_has_enough_cases() -> None:
    df = load_gold_dataset(GOLD_PATH)

    assert len(df) >= 15
    assert {"Positive", "Cautionary", "Irrelevant"}.issubset(set(df["expected_target_sentiment"]))


def test_lightweight_sentiment_meets_initial_gold_thresholds() -> None:
    metrics, details = evaluate_from_path(SentimentEvaluationConfig(gold_path=GOLD_PATH, engine="lightweight"))

    assert metrics["headline_count"] == len(details)
    assert metrics["target_accuracy"] >= 0.75
    assert metrics["target_macro_f1"] >= 0.70
    assert metrics["cautionary_recall"] >= 0.75


def test_play_buy_instead_case_stays_cautionary_in_gold_eval() -> None:
    _, details = evaluate_from_path(SentimentEvaluationConfig(gold_path=GOLD_PATH, engine="lightweight"))
    row = details[details["title"].str.contains("Risky and 1 Stock to Buy Instead", case=False, regex=False)].iloc[0]

    assert row["predicted_target_sentiment"] == "Cautionary"
    assert row["target_match"] is True or bool(row["target_match"])
