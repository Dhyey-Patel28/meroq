from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.model import (
    FEATURE_COLUMNS,
    MODEL_LABELS,
    classification_metrics,
    force_numeric_features,
    make_classifier,
)


SENTIMENT_MODEL_FEATURE_COLUMNS = [
    "sentiment_available",
    "sentiment_headline_count",
    "sentiment_mean",
    "sentiment_std",
    "positive_ratio",
    "negative_ratio",
    "neutral_ratio",
    "confidence_mean",
]


@dataclass(frozen=True)
class SentimentModelingReadiness:
    total_model_rows: int
    aligned_sentiment_rows: int
    sentiment_coverage: float
    first_sentiment_date: str | None
    latest_sentiment_date: str | None
    ready_for_experiment: bool
    note: str

    def as_dict(self) -> dict:
        return {
            "total_model_rows": self.total_model_rows,
            "aligned_sentiment_rows": self.aligned_sentiment_rows,
            "sentiment_coverage": self.sentiment_coverage,
            "first_sentiment_date": self.first_sentiment_date,
            "latest_sentiment_date": self.latest_sentiment_date,
            "ready_for_experiment": self.ready_for_experiment,
            "note": self.note,
        }


def _empty_daily_sentiment() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "ticker",
            "headline_count",
            "sentiment_mean",
            "sentiment_std",
            "positive_ratio",
            "negative_ratio",
            "neutral_ratio",
            "confidence_mean",
        ]
    )


def prepare_daily_sentiment_for_join(
    daily_sentiment: pd.DataFrame | None,
    lag_days: int = 1,
) -> pd.DataFrame:
    """
    Prepare daily sentiment features for joining to price rows.

    The default one-day lag is intentional. It avoids accidentally training on
    news that may have been published after the market close on the same date.
    The feature row for price date T therefore uses sentiment observed on date
    T - lag_days.
    """
    if daily_sentiment is None or daily_sentiment.empty:
        return _empty_daily_sentiment().assign(join_date=pd.NaT)

    data = daily_sentiment.copy()
    if "date" not in data.columns:
        return _empty_daily_sentiment().assign(join_date=pd.NaT)

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["date"])
    if data.empty:
        return _empty_daily_sentiment().assign(join_date=pd.NaT)

    for col in [
        "headline_count",
        "sentiment_mean",
        "sentiment_std",
        "positive_ratio",
        "negative_ratio",
        "neutral_ratio",
        "confidence_mean",
    ]:
        if col not in data.columns:
            data[col] = 0.0
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0.0)

    data["join_date"] = data["date"] + pd.to_timedelta(int(lag_days), unit="D")
    data["join_date"] = data["join_date"].dt.normalize()
    return data.sort_values("date").reset_index(drop=True)


def build_sentiment_enhanced_model_frame(
    model_frame: pd.DataFrame,
    daily_sentiment: pd.DataFrame | None,
    lag_days: int = 1,
) -> pd.DataFrame:
    """
    Join lagged daily sentiment features to the standard model frame.

    Missing sentiment is filled with neutral/default values so the frame remains
    usable even while Meroq is still accumulating historical news coverage.
    """
    if model_frame is None or model_frame.empty:
        return pd.DataFrame()

    base = model_frame.copy()
    base["Date"] = pd.to_datetime(base["Date"], errors="coerce")
    base = base.dropna(subset=["Date"]).copy()
    base["join_date"] = base["Date"].dt.normalize()

    sent = prepare_daily_sentiment_for_join(daily_sentiment, lag_days=lag_days)
    keep_cols = [
        "join_date",
        "headline_count",
        "sentiment_mean",
        "sentiment_std",
        "positive_ratio",
        "negative_ratio",
        "neutral_ratio",
        "confidence_mean",
    ]
    sent = sent[[col for col in keep_cols if col in sent.columns]].copy()

    if sent.empty:
        merged = base.copy()
        for col in SENTIMENT_MODEL_FEATURE_COLUMNS:
            merged[col] = 0.0
        return merged.drop(columns=["join_date"], errors="ignore")

    merged = base.merge(sent, on="join_date", how="left", suffixes=("", "_sentiment"))
    merged["sentiment_headline_count"] = pd.to_numeric(merged.get("headline_count"), errors="coerce").fillna(0.0)
    merged["sentiment_available"] = (merged["sentiment_headline_count"] > 0).astype(float)

    for col in [
        "sentiment_mean",
        "sentiment_std",
        "positive_ratio",
        "negative_ratio",
        "neutral_ratio",
        "confidence_mean",
    ]:
        if col not in merged.columns:
            merged[col] = 0.0
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0.0)

    return merged.drop(columns=["join_date", "headline_count"], errors="ignore")


def analyze_sentiment_modeling_readiness(
    model_frame: pd.DataFrame,
    daily_sentiment: pd.DataFrame | None,
    min_aligned_rows: int = 30,
    lag_days: int = 1,
) -> SentimentModelingReadiness:
    """Return a compact readiness summary for sentiment-aware modeling."""
    enhanced = build_sentiment_enhanced_model_frame(model_frame, daily_sentiment, lag_days=lag_days)
    total_rows = int(len(enhanced))
    aligned_rows = int((pd.to_numeric(enhanced.get("sentiment_headline_count", 0), errors="coerce").fillna(0) > 0).sum())
    coverage = float(aligned_rows / total_rows) if total_rows else 0.0

    sent = prepare_daily_sentiment_for_join(daily_sentiment, lag_days=lag_days)
    if sent.empty or "date" not in sent.columns:
        first_date = None
        latest_date = None
    else:
        first_date = sent["date"].min().date().isoformat()
        latest_date = sent["date"].max().date().isoformat()

    ready = aligned_rows >= int(min_aligned_rows)
    if ready:
        note = "Enough aligned sentiment rows for a first experimental comparison."
    elif aligned_rows == 0:
        note = "No sentiment rows are aligned to model dates yet. Keep caching news over time or run scheduled refreshes."
    else:
        note = (
            f"Only {aligned_rows} aligned sentiment rows are available. This is useful for feature auditing, "
            f"but not enough for a reliable sentiment-trained model yet."
        )

    return SentimentModelingReadiness(
        total_model_rows=total_rows,
        aligned_sentiment_rows=aligned_rows,
        sentiment_coverage=coverage,
        first_sentiment_date=first_date,
        latest_sentiment_date=latest_date,
        ready_for_experiment=ready,
        note=note,
    )


def _force_custom_numeric_features(df: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    data = df.copy()
    for col in feature_columns:
        if col not in data.columns:
            data[col] = 0.0
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data["target_up_tomorrow"] = pd.to_numeric(data["target_up_tomorrow"], errors="coerce")
    if "Date" in data.columns:
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    if "next_return" in data.columns:
        data["next_return"] = pd.to_numeric(data["next_return"], errors="coerce")

    data = data.replace([np.inf, -np.inf], np.nan)
    return data.dropna(subset=feature_columns + ["target_up_tomorrow"]).reset_index(drop=True)


def _predict_up_probability(model, X: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)
        if proba.ndim == 2 and proba.shape[1] >= 2:
            return proba[:, 1].astype(float)
    if hasattr(model, "decision_function"):
        scores = model.decision_function(X)
        return (1 / (1 + np.exp(-scores))).astype(float)
    pred = model.predict(X)
    return np.where(pred == 1, 0.55, 0.45).astype(float)


def compare_base_vs_sentiment_simple_split(
    model_frame: pd.DataFrame,
    daily_sentiment: pd.DataFrame | None,
    model_name: str = "xgboost",
    test_size: float = 0.2,
    min_rows: int = 120,
    min_aligned_rows: int = 30,
    lag_days: int = 1,
    n_estimators: int = 120,
) -> dict:
    """
    Compare a base technical model against a sentiment-enhanced variant.

    This is an experiment, not a production-quality historical sentiment model.
    It becomes more meaningful as the local sentiment feature store grows.
    """
    if model_name not in MODEL_LABELS:
        raise ValueError(f"Unknown model_name '{model_name}'. Choose from: {list(MODEL_LABELS)}")

    readiness = analyze_sentiment_modeling_readiness(
        model_frame,
        daily_sentiment,
        min_aligned_rows=min_aligned_rows,
        lag_days=lag_days,
    )

    enhanced = build_sentiment_enhanced_model_frame(model_frame, daily_sentiment, lag_days=lag_days)
    sentiment_feature_columns = FEATURE_COLUMNS + SENTIMENT_MODEL_FEATURE_COLUMNS

    base_data = force_numeric_features(enhanced)
    sentiment_data = _force_custom_numeric_features(enhanced, sentiment_feature_columns)

    if len(base_data) < min_rows or len(sentiment_data) < min_rows:
        return {
            "available": False,
            "reason": f"Not enough usable rows. Need at least {min_rows}; got base={len(base_data)}, sentiment={len(sentiment_data)}.",
            "readiness": readiness.as_dict(),
            "comparison": pd.DataFrame(),
            "sentiment_feature_preview": sentiment_data.tail(20),
        }

    split_idx = int(len(base_data) * (1 - test_size))
    base_train = base_data.iloc[:split_idx].copy()
    base_test = base_data.iloc[split_idx:].copy()

    # Use the same chronological split points for the sentiment data.
    sentiment_train = sentiment_data.iloc[:split_idx].copy()
    sentiment_test = sentiment_data.iloc[split_idx:].copy()

    y_train = base_train["target_up_tomorrow"].astype("int64")
    y_test = base_test["target_up_tomorrow"].astype("int64")

    base_model = make_classifier(model_name=model_name, n_estimators=n_estimators)
    sentiment_model = make_classifier(model_name=model_name, n_estimators=n_estimators)

    base_model.fit(base_train[FEATURE_COLUMNS].astype("float64"), y_train)
    sentiment_model.fit(sentiment_train[sentiment_feature_columns].astype("float64"), y_train)

    base_proba = _predict_up_probability(base_model, base_test[FEATURE_COLUMNS].astype("float64"))
    sentiment_proba = _predict_up_probability(
        sentiment_model,
        sentiment_test[sentiment_feature_columns].astype("float64"),
    )

    base_pred = (base_proba >= 0.5).astype(int)
    sentiment_pred = (sentiment_proba >= 0.5).astype(int)

    base_metrics = classification_metrics(y_test, base_pred, base_proba)
    sentiment_metrics = classification_metrics(y_test, sentiment_pred, sentiment_proba)

    comparison = pd.DataFrame(
        [
            {
                "variant": "Technical features only",
                "model": MODEL_LABELS[model_name],
                **base_metrics,
                "train_rows": len(base_train),
                "test_rows": len(base_test),
            },
            {
                "variant": "Technical + lagged sentiment",
                "model": MODEL_LABELS[model_name],
                **sentiment_metrics,
                "train_rows": len(sentiment_train),
                "test_rows": len(sentiment_test),
            },
        ]
    )

    return {
        "available": True,
        "ready_for_experiment": readiness.ready_for_experiment,
        "reason": readiness.note,
        "readiness": readiness.as_dict(),
        "comparison": comparison,
        "sentiment_feature_preview": sentiment_data[
            ["Date", "target_up_tomorrow"] + SENTIMENT_MODEL_FEATURE_COLUMNS
        ].tail(50),
        "base_probabilities": base_proba,
        "sentiment_probabilities": sentiment_proba,
        "test_dates": base_test.get("Date"),
    }
