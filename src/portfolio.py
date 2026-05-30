from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


REQUIRED_SCAN_COLUMNS = [
    "ticker",
    "status",
    "latest_close",
    "return_1d",
    "final_up_probability",
    "sentiment_score",
    "risk_loss_gt_5pct",
    "risk_positive_probability",
    "meroq_score",
]


def parse_portfolio_weights(tickers: Iterable[str], weights_text: str | None = None) -> pd.DataFrame:
    """Parse optional user weights into a normalized holdings table.

    Supported formats in ``weights_text``:
    - ``AAPL:40, MSFT:30, SPY:30``
    - ``AAPL=0.4, MSFT=0.3, SPY=0.3``
    - blank input means equal weight.

    Values can be percentages or decimals. The function normalizes all positive
    weights to sum to 1. Missing tickers are assigned equal residual weight.
    """
    symbols = [str(t).upper().strip() for t in tickers if str(t).strip()]
    symbols = list(dict.fromkeys(symbols))
    if not symbols:
        return pd.DataFrame(columns=["ticker", "weight"])

    parsed: dict[str, float] = {}
    text = (weights_text or "").strip()
    if text:
        chunks = text.replace("\n", ",").split(",")
        for chunk in chunks:
            item = chunk.strip()
            if not item:
                continue
            if ":" in item:
                key, value = item.split(":", 1)
            elif "=" in item:
                key, value = item.split("=", 1)
            else:
                continue
            symbol = key.upper().strip()
            if symbol not in symbols:
                continue
            try:
                weight = float(value.strip().replace("%", ""))
            except ValueError:
                continue
            if weight > 1.0:
                weight = weight / 100.0
            if weight > 0:
                parsed[symbol] = weight

    if not parsed:
        equal_weight = 1.0 / len(symbols)
        return pd.DataFrame({"ticker": symbols, "weight": [equal_weight] * len(symbols)})

    remaining = [s for s in symbols if s not in parsed]
    used = sum(parsed.values())
    if remaining:
        residual = max(0.0, 1.0 - used)
        fill = residual / len(remaining) if residual > 0 else 1.0 / len(symbols)
        for symbol in remaining:
            parsed[symbol] = fill

    total = sum(max(0.0, value) for value in parsed.values())
    if total <= 0:
        equal_weight = 1.0 / len(symbols)
        return pd.DataFrame({"ticker": symbols, "weight": [equal_weight] * len(symbols)})

    rows = [{"ticker": symbol, "weight": max(0.0, parsed.get(symbol, 0.0)) / total} for symbol in symbols]
    return pd.DataFrame(rows)


def build_portfolio_view(scan_df: pd.DataFrame, weights_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Join watchlist scan output with weights and compute portfolio metrics."""
    if scan_df is None or scan_df.empty or weights_df is None or weights_df.empty:
        return pd.DataFrame(), _empty_summary()

    ok = scan_df[scan_df.get("status", "") == "ok"].copy()
    if ok.empty:
        return pd.DataFrame(), _empty_summary()

    weights = weights_df.copy()
    weights["ticker"] = weights["ticker"].astype(str).str.upper().str.strip()
    weights["weight"] = pd.to_numeric(weights["weight"], errors="coerce").fillna(0.0)
    weights = weights[weights["weight"] > 0]

    holdings = ok.merge(weights, on="ticker", how="inner")
    if holdings.empty:
        return pd.DataFrame(), _empty_summary()

    holdings["weight"] = holdings["weight"] / holdings["weight"].sum()

    numeric_cols = [
        "latest_close",
        "return_1d",
        "final_up_probability",
        "base_up_probability",
        "sentiment_score",
        "risk_loss_gt_5pct",
        "risk_positive_probability",
        "risk_median_return",
        "meroq_score",
        "model_roc_auc",
    ]
    for col in numeric_cols:
        if col in holdings.columns:
            holdings[col] = pd.to_numeric(holdings[col], errors="coerce")

    holdings["weighted_meroq_score"] = holdings["weight"] * holdings.get("meroq_score", 0.0)
    holdings["weighted_up_probability"] = holdings["weight"] * holdings.get("final_up_probability", 0.0)
    holdings["weighted_downside_probability"] = holdings["weight"] * holdings.get("risk_loss_gt_5pct", 0.0)
    holdings["weighted_sentiment_score"] = holdings["weight"] * holdings.get("sentiment_score", 0.0)
    holdings["weighted_daily_return"] = holdings["weight"] * holdings.get("return_1d", 0.0)

    summary = {
        "positions": int(len(holdings)),
        "total_weight": float(holdings["weight"].sum()),
        "portfolio_meroq_score": float(holdings["weighted_meroq_score"].sum()),
        "weighted_up_probability": float(holdings["weighted_up_probability"].sum()),
        "weighted_downside_probability": float(holdings["weighted_downside_probability"].sum()),
        "weighted_sentiment_score": float(holdings["weighted_sentiment_score"].sum()),
        "weighted_daily_return": float(holdings["weighted_daily_return"].sum()),
        "bullish_weight": _weighted_label_share(holdings, "final_signal", "Bullish"),
        "bearish_weight": _weighted_label_share(holdings, "final_signal", "Bearish"),
        "positive_sentiment_weight": _weighted_label_share(holdings, "sentiment_label", "Positive"),
        "high_risk_weight": float(holdings.loc[holdings.get("risk_label", "").astype(str).str.contains("High|Elevated", case=False, na=False), "weight"].sum()) if "risk_label" in holdings else 0.0,
    }
    summary["portfolio_risk_label"] = _portfolio_risk_label(summary)
    summary["portfolio_signal_label"] = _portfolio_signal_label(summary)

    display_order = [
        "ticker",
        "weight",
        "latest_close",
        "return_1d",
        "final_signal",
        "final_up_probability",
        "sentiment_label",
        "sentiment_score",
        "risk_label",
        "risk_loss_gt_5pct",
        "meroq_score",
        "weighted_meroq_score",
    ]
    available = [col for col in display_order if col in holdings.columns]
    extra = [col for col in holdings.columns if col not in available]
    holdings = holdings[available + extra].sort_values("weight", ascending=False).reset_index(drop=True)
    return holdings, summary


def _weighted_label_share(df: pd.DataFrame, column: str, label: str) -> float:
    if column not in df.columns or "weight" not in df.columns:
        return 0.0
    return float(df.loc[df[column].astype(str).str.lower() == label.lower(), "weight"].sum())


def _portfolio_risk_label(summary: dict) -> str:
    downside = float(summary.get("weighted_downside_probability", 0.0) or 0.0)
    high_risk_weight = float(summary.get("high_risk_weight", 0.0) or 0.0)
    if downside >= 0.32 or high_risk_weight >= 0.35:
        return "Elevated portfolio risk"
    if downside <= 0.18 and high_risk_weight <= 0.15:
        return "Constructive portfolio risk"
    return "Balanced portfolio risk"


def _portfolio_signal_label(summary: dict) -> str:
    up_probability = float(summary.get("weighted_up_probability", 0.0) or 0.0)
    score = float(summary.get("portfolio_meroq_score", 0.0) or 0.0)
    if up_probability >= 0.56 and score >= 57:
        return "Constructive"
    if up_probability <= 0.44 or score <= 43:
        return "Cautious"
    return "Neutral"


def _empty_summary() -> dict:
    return {
        "positions": 0,
        "total_weight": 0.0,
        "portfolio_meroq_score": 0.0,
        "weighted_up_probability": 0.0,
        "weighted_downside_probability": 0.0,
        "weighted_sentiment_score": 0.0,
        "weighted_daily_return": 0.0,
        "bullish_weight": 0.0,
        "bearish_weight": 0.0,
        "positive_sentiment_weight": 0.0,
        "high_risk_weight": 0.0,
        "portfolio_risk_label": "Unavailable",
        "portfolio_signal_label": "Unavailable",
    }


def portfolio_summary_sentence(summary: dict) -> str:
    """Human-readable portfolio interpretation for the UI/report."""
    if not summary or int(summary.get("positions", 0) or 0) == 0:
        return "Portfolio view is unavailable until at least one position is scanned successfully."
    return (
        f"The scanned portfolio has a {summary.get('portfolio_signal_label', 'Neutral').lower()} signal profile, "
        f"a Meroq score of {float(summary.get('portfolio_meroq_score', 0.0)):.1f}/100, "
        f"weighted up probability of {float(summary.get('weighted_up_probability', 0.0)):.1%}, "
        f"and {summary.get('portfolio_risk_label', 'balanced risk').lower()}."
    )
