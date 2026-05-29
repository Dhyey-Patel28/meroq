from __future__ import annotations

import pandas as pd


def aggregate_daily_sentiment(sentiment_df: pd.DataFrame, ticker: str | None = None) -> pd.DataFrame:
    """
    Aggregate headline-level sentiment into daily features.

    These features are designed for the next modeling step: joining daily sentiment
    to daily OHLCV rows, then comparing models with and without sentiment.
    """
    if sentiment_df is None or sentiment_df.empty:
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

    data = sentiment_df.copy()
    data["published_at"] = pd.to_datetime(data.get("published_at"), errors="coerce", utc=True)
    data = data.dropna(subset=["published_at"])
    if data.empty:
        return pd.DataFrame()

    data["date"] = data["published_at"].dt.date.astype(str)
    data["sentiment_score"] = pd.to_numeric(data.get("sentiment_score", 0.0), errors="coerce").fillna(0.0)
    data["confidence"] = pd.to_numeric(data.get("confidence", 0.0), errors="coerce").fillna(0.0)
    data["sentiment_label"] = data.get("sentiment_label", "neutral").astype(str).str.lower()

    grouped = data.groupby("date", as_index=False).agg(
        headline_count=("title", "count"),
        sentiment_mean=("sentiment_score", "mean"),
        sentiment_std=("sentiment_score", "std"),
        confidence_mean=("confidence", "mean"),
    )

    label_counts = (
        data.assign(value=1)
        .pivot_table(index="date", columns="sentiment_label", values="value", aggfunc="sum", fill_value=0)
        .reset_index()
    )

    merged = grouped.merge(label_counts, on="date", how="left")
    for col in ["positive", "negative", "neutral"]:
        if col not in merged.columns:
            merged[col] = 0

    merged["positive_ratio"] = merged["positive"] / merged["headline_count"].replace(0, pd.NA)
    merged["negative_ratio"] = merged["negative"] / merged["headline_count"].replace(0, pd.NA)
    merged["neutral_ratio"] = merged["neutral"] / merged["headline_count"].replace(0, pd.NA)
    merged["sentiment_std"] = merged["sentiment_std"].fillna(0.0)
    merged["ticker"] = (ticker or "").upper()

    return merged[
        [
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
    ].sort_values("date", ascending=False).reset_index(drop=True)


def build_latest_sentiment_feature_row(daily_sentiment: pd.DataFrame) -> dict:
    """Create a compact latest-feature dictionary for summaries/logging."""
    if daily_sentiment is None or daily_sentiment.empty:
        return {
            "available": False,
            "headline_count": 0,
            "sentiment_mean": 0.0,
            "positive_ratio": 0.0,
            "negative_ratio": 0.0,
        }

    row = daily_sentiment.iloc[0]
    return {
        "available": True,
        "date": row.get("date"),
        "headline_count": int(row.get("headline_count", 0) or 0),
        "sentiment_mean": float(row.get("sentiment_mean", 0.0) or 0.0),
        "positive_ratio": float(row.get("positive_ratio", 0.0) or 0.0),
        "negative_ratio": float(row.get("negative_ratio", 0.0) or 0.0),
        "confidence_mean": float(row.get("confidence_mean", 0.0) or 0.0),
    }
