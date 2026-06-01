from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import pandas as pd

from src.grades import grade_label, score_to_grade


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

GRADE_ORDER = ["A", "B", "C", "D", "F", "N/A"]


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
    """Join watchlist scan output with weights and compute portfolio command-center metrics."""
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

    total_score_contribution = _safe_sum(holdings["weighted_meroq_score"])
    total_downside_contribution = _safe_sum(holdings["weighted_downside_probability"])
    holdings["score_contribution_share"] = _share_series(holdings["weighted_meroq_score"], total_score_contribution)
    holdings["downside_contribution_share"] = _share_series(holdings["weighted_downside_probability"], total_downside_contribution)

    research_weights = _research_weight_series(holdings)
    holdings["research_weight"] = research_weights
    holdings["research_weight_delta"] = holdings["research_weight"] - holdings["weight"]
    holdings["exposure_note"] = holdings.apply(_holding_exposure_note, axis=1)
    holdings["allocation_review"] = holdings.apply(_allocation_review_note, axis=1)

    weighted_meroq_score = float(holdings["weighted_meroq_score"].sum())
    holding_count = int(len(holdings))
    largest = _first_record(holdings.sort_values("weight", ascending=False))
    concentration_score = float((holdings["weight"] ** 2).sum())
    concentration_label = _concentration_label(largest.get("weight"), concentration_score, holding_count)
    grade_distribution = _grade_distribution(holdings)
    top_score_contributors = _portfolio_records(holdings, "weighted_meroq_score", 3)
    top_risk_contributors = _portfolio_records(holdings, "weighted_downside_probability", 3)
    weakest_holdings = _portfolio_records(holdings, "meroq_score", 3, ascending=True)
    highest_risk_holdings = _portfolio_records(holdings, "risk_loss_gt_5pct", 3)
    scenario_comparison = build_portfolio_scenarios(holdings)
    research_scenario = next((row for row in scenario_comparison if row.get("scenario_key") == "research_weighted"), {})
    research_adds = _allocation_shift_records(holdings, positive=True, limit=3)
    research_trims = _allocation_shift_records(holdings, positive=False, limit=3)

    portfolio_grade = score_to_grade(weighted_meroq_score)
    summary = {
        # Canonical public keys used by the UI, API, reports, and tests.
        "holding_count": holding_count,
        "weighted_meroq_score": weighted_meroq_score,
        "portfolio_grade": portfolio_grade,
        "portfolio_grade_label": grade_label(portfolio_grade),
        "total_weight": float(holdings["weight"].sum()),
        "weighted_up_probability": float(holdings["weighted_up_probability"].sum()),
        "weighted_downside_probability": float(holdings["weighted_downside_probability"].sum()),
        "weighted_sentiment_score": float(holdings["weighted_sentiment_score"].sum()),
        "weighted_daily_return": float(holdings["weighted_daily_return"].sum()),
        "bullish_weight": _weighted_label_share(holdings, "final_signal", "Bullish"),
        "bearish_weight": _weighted_label_share(holdings, "final_signal", "Bearish"),
        "positive_sentiment_weight": _weighted_label_share(holdings, "sentiment_label", "Positive"),
        "high_risk_weight": _high_risk_weight(holdings),
        # 1.9.3 command-center fields.
        "largest_position_ticker": largest.get("ticker"),
        "largest_position_weight": largest.get("weight", 0.0),
        "concentration_score": concentration_score,
        "concentration_label": concentration_label,
        "portfolio_health_label": _portfolio_health_label(weighted_meroq_score, concentration_label),
        "grade_distribution": grade_distribution,
        "top_score_contributors": top_score_contributors,
        "top_risk_contributors": top_risk_contributors,
        "weakest_holdings": weakest_holdings,
        "highest_risk_holdings": highest_risk_holdings,
        # 1.9.4 scenario-lab fields.
        "scenario_comparison": scenario_comparison,
        "research_weighted_scenario": research_scenario,
        "research_adds": research_adds,
        "research_trims": research_trims,
        "scenario_disclaimer": "Scenario weights are diagnostic what-if views, not allocation advice.",
    }

    # Backward-compatible aliases retained for existing app/report code.
    summary["positions"] = holding_count
    summary["portfolio_meroq_score"] = weighted_meroq_score
    summary["portfolio_risk_label"] = _portfolio_risk_label(summary)
    summary["portfolio_signal_label"] = _portfolio_signal_label(summary)
    summary["portfolio_alerts"] = build_portfolio_alerts(summary)

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
        "meroq_grade",
        "momentum_grade",
        "risk_grade",
        "sentiment_grade",
        "model_confidence_grade",
        "weighted_meroq_score",
        "score_contribution_share",
        "downside_contribution_share",
        "research_weight",
        "research_weight_delta",
        "allocation_review",
        "exposure_note",
    ]
    available = [col for col in display_order if col in holdings.columns]
    extra = [col for col in holdings.columns if col not in available]
    holdings = holdings[available + extra].sort_values("weight", ascending=False).reset_index(drop=True)
    return holdings, summary


def build_portfolio_alerts(summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Return concise command-center cards for the portfolio page."""
    if not summary or int(summary.get("holding_count", 0) or 0) == 0:
        return []

    alerts: list[dict[str, Any]] = []
    concentration = str(summary.get("concentration_label", "Balanced"))
    largest_ticker = summary.get("largest_position_ticker") or "largest position"
    largest_weight = float(summary.get("largest_position_weight", 0.0) or 0.0)
    if concentration == "Concentrated":
        alerts.append(
            {
                "title": "Concentration needs attention",
                "severity": "warning",
                "ticker": largest_ticker,
                "metric": largest_weight,
                "detail": f"{largest_ticker} is the largest position at {largest_weight:.1%}. Review whether one holding is carrying too much of the portfolio read.",
            }
        )
    else:
        alerts.append(
            {
                "title": "Allocation is reasonably spread",
                "severity": "positive" if concentration == "Diversified" else "neutral",
                "ticker": largest_ticker,
                "metric": largest_weight,
                "detail": f"Largest position is {largest_ticker} at {largest_weight:.1%}; concentration label is {concentration.lower()}.",
            }
        )

    risk_contributors = summary.get("top_risk_contributors") or []
    if risk_contributors:
        top_risk = risk_contributors[0]
        risk_share = float(top_risk.get("downside_contribution_share", 0.0) or 0.0)
        alerts.append(
            {
                "title": "Top downside driver",
                "severity": "warning" if risk_share >= 0.35 else "neutral",
                "ticker": top_risk.get("ticker"),
                "metric": risk_share,
                "detail": f"{top_risk.get('ticker')} contributes {risk_share:.1%} of weighted downside probability in this scan.",
            }
        )

    weakest = summary.get("weakest_holdings") or []
    if weakest:
        weak = weakest[0]
        score = float(weak.get("meroq_score", 0.0) or 0.0)
        alerts.append(
            {
                "title": "Weakest current setup",
                "severity": "negative" if score < 42 else "neutral",
                "ticker": weak.get("ticker"),
                "metric": score,
                "detail": f"{weak.get('ticker')} has the lowest Meroq Score in the portfolio at {score:.1f}/100.",
            }
        )

    grade_distribution = summary.get("grade_distribution") or []
    caution_weight = sum(float(row.get("weight", 0.0) or 0.0) for row in grade_distribution if row.get("grade") in {"D", "F"})
    alerts.append(
        {
            "title": "Caution-grade exposure",
            "severity": "warning" if caution_weight >= 0.25 else "positive",
            "metric": caution_weight,
            "detail": f"D/F grade exposure is {caution_weight:.1%} of scanned portfolio weight.",
        }
    )
    return alerts


def _weighted_label_share(df: pd.DataFrame, column: str, label: str) -> float:
    if column not in df.columns or "weight" not in df.columns:
        return 0.0
    return float(df.loc[df[column].astype(str).str.lower() == label.lower(), "weight"].sum())


def _high_risk_weight(holdings: pd.DataFrame) -> float:
    if "risk_label" not in holdings:
        return 0.0
    mask = holdings["risk_label"].astype(str).str.contains("High|Elevated", case=False, na=False)
    return float(holdings.loc[mask, "weight"].sum())


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
        "holding_count": 0,
        "positions": 0,
        "total_weight": 0.0,
        "weighted_meroq_score": 0.0,
        "portfolio_grade": "N/A",
        "portfolio_grade_label": "Unavailable",
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
        "largest_position_ticker": None,
        "largest_position_weight": 0.0,
        "concentration_score": 0.0,
        "concentration_label": "Unavailable",
        "portfolio_health_label": "Unavailable",
        "grade_distribution": [],
        "top_score_contributors": [],
        "top_risk_contributors": [],
        "weakest_holdings": [],
        "highest_risk_holdings": [],
        "scenario_comparison": [],
        "research_weighted_scenario": {},
        "research_adds": [],
        "research_trims": [],
        "scenario_disclaimer": "Scenario weights are diagnostic what-if views, not allocation advice.",
        "portfolio_alerts": [],
    }


def portfolio_summary_sentence(summary: dict) -> str:
    """Human-readable portfolio interpretation for the UI/report."""
    holding_count = int(summary.get("holding_count", summary.get("positions", 0)) or 0)
    if not summary or holding_count == 0:
        return "Portfolio view is unavailable until at least one position is scanned successfully."
    score = float(summary.get("weighted_meroq_score", summary.get("portfolio_meroq_score", 0.0)) or 0.0)
    concentration = summary.get("concentration_label", "balanced")
    largest = summary.get("largest_position_ticker") or "largest holding"
    largest_weight = float(summary.get("largest_position_weight", 0.0) or 0.0)
    return (
        f"The scanned portfolio has a {summary.get('portfolio_signal_label', 'Neutral').lower()} signal profile, "
        f"a {summary.get('portfolio_grade', 'N/A')} portfolio grade, "
        f"a Meroq score of {score:.1f}/100, "
        f"weighted up probability of {float(summary.get('weighted_up_probability', 0.0)):.1%}, "
        f"{summary.get('portfolio_risk_label', 'balanced risk').lower()}, "
        f"and {str(concentration).lower()} allocation with {largest} at {largest_weight:.1%}."
    )


def _share_series(series: pd.Series, total: float) -> pd.Series:
    if total <= 0:
        return pd.Series([0.0] * len(series), index=series.index)
    return pd.to_numeric(series, errors="coerce").fillna(0.0) / total


def _safe_sum(series: pd.Series) -> float:
    return float(pd.to_numeric(series, errors="coerce").fillna(0.0).sum())


def _first_record(df: pd.DataFrame) -> dict[str, Any]:
    if df is None or df.empty:
        return {}
    return df.iloc[0].to_dict()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(number):
        return default
    return number


def _concentration_label(largest_weight: Any, concentration_score: float, holding_count: int) -> str:
    largest = _safe_float(largest_weight)
    if holding_count <= 1 or largest >= 0.35 or concentration_score >= 0.22:
        return "Concentrated"
    if largest <= 0.18 and concentration_score <= 0.14 and holding_count >= 6:
        return "Diversified"
    return "Moderate"


def _portfolio_health_label(weighted_meroq_score: float, concentration_label: str) -> str:
    if weighted_meroq_score >= 62 and concentration_label != "Concentrated":
        return "Constructive command center"
    if weighted_meroq_score <= 43:
        return "Caution command center"
    if concentration_label == "Concentrated":
        return "Concentration-led read"
    return "Balanced command center"


def _grade_distribution(holdings: pd.DataFrame) -> list[dict[str, Any]]:
    if "meroq_grade" not in holdings.columns:
        return []
    rows: list[dict[str, Any]] = []
    for grade in GRADE_ORDER:
        if grade == "N/A":
            mask = ~holdings["meroq_grade"].astype(str).str.upper().isin(GRADE_ORDER[:-1])
        else:
            mask = holdings["meroq_grade"].astype(str).str.upper() == grade
        count = int(mask.sum())
        weight = float(holdings.loc[mask, "weight"].sum()) if "weight" in holdings else 0.0
        if count or weight:
            rows.append({"grade": grade, "count": count, "weight": weight, "label": grade_label(grade) if grade != "N/A" else "Unrated"})
    return rows


def _portfolio_records(holdings: pd.DataFrame, sort_column: str, limit: int, ascending: bool = False) -> list[dict[str, Any]]:
    if holdings.empty or sort_column not in holdings.columns:
        return []
    columns = [
        "ticker",
        "weight",
        "meroq_score",
        "meroq_grade",
        "final_signal",
        "final_up_probability",
        "risk_label",
        "risk_loss_gt_5pct",
        "sentiment_label",
        "weighted_meroq_score",
        "weighted_downside_probability",
        "score_contribution_share",
        "downside_contribution_share",
        "research_weight",
        "research_weight_delta",
        "allocation_review",
        "exposure_note",
    ]
    available = [col for col in columns if col in holdings.columns]
    ranked = holdings.sort_values(sort_column, ascending=ascending, na_position="last").head(limit)
    records = []
    for row in ranked[available].to_dict(orient="records"):
        records.append({key: _json_safe(value) for key, value in row.items()})
    return records


def _allocation_shift_records(holdings: pd.DataFrame, *, positive: bool, limit: int) -> list[dict[str, Any]]:
    if holdings.empty or "research_weight_delta" not in holdings.columns:
        return []
    deltas = pd.to_numeric(holdings["research_weight_delta"], errors="coerce").fillna(0.0)
    mask = deltas > 0 if positive else deltas < 0
    filtered = holdings.loc[mask].copy()
    if filtered.empty:
        return []
    return _portfolio_records(filtered, "research_weight_delta", limit, ascending=not positive)


def build_portfolio_scenarios(holdings: pd.DataFrame) -> list[dict[str, Any]]:
    """Build transparent what-if allocation scenarios from existing scan rows.

    The output is diagnostic. It compares the user's current weights with equal
    weighting and a local research-weighted tilt that favors stronger Meroq
    scores while penalizing downside-risk fields. It does not optimize a real
    portfolio or provide allocation advice.
    """
    if holdings is None or holdings.empty:
        return []

    n = len(holdings)
    current = _normalize_weight_series(holdings.get("weight", pd.Series(dtype=float)))
    equal = pd.Series([1.0 / n] * n, index=holdings.index)
    research = _research_weight_series(holdings)

    scenarios = [
        _scenario_metrics(
            holdings,
            current,
            scenario_key="current",
            label="Current weights",
            description="Uses the weights you entered for the current scan.",
        ),
        _scenario_metrics(
            holdings,
            equal,
            scenario_key="equal_weight",
            label="Equal-weight check",
            description="Shows how the same holdings look when each ticker has the same weight.",
        ),
        _scenario_metrics(
            holdings,
            research,
            scenario_key="research_weighted",
            label="Research-weighted scenario",
            description="Tilts weight toward stronger local Meroq scores and away from higher downside-risk readings.",
        ),
    ]

    baseline = scenarios[0]
    for scenario in scenarios:
        scenario["score_delta"] = float(scenario["weighted_meroq_score"] - baseline["weighted_meroq_score"])
        scenario["up_probability_delta"] = float(scenario["weighted_up_probability"] - baseline["weighted_up_probability"])
        scenario["downside_delta"] = float(scenario["weighted_downside_probability"] - baseline["weighted_downside_probability"])
        scenario["high_risk_weight_delta"] = float(scenario["high_risk_weight"] - baseline["high_risk_weight"])
        scenario["summary"] = _scenario_summary(scenario)
    return scenarios


def _scenario_metrics(
    holdings: pd.DataFrame,
    weights: pd.Series,
    *,
    scenario_key: str,
    label: str,
    description: str,
) -> dict[str, Any]:
    normalized = _normalize_weight_series(weights)
    if normalized.empty:
        normalized = pd.Series([1.0 / len(holdings)] * len(holdings), index=holdings.index)

    weighted_meroq_score = _weighted_sum(holdings, "meroq_score", normalized)
    largest_idx = normalized.idxmax() if len(normalized) else None
    largest_ticker = str(holdings.loc[largest_idx, "ticker"]) if largest_idx is not None and "ticker" in holdings else None
    largest_weight = float(normalized.max()) if len(normalized) else 0.0
    concentration_score = float((normalized ** 2).sum())
    concentration_label = _concentration_label(largest_weight, concentration_score, len(holdings))

    scenario = {
        "scenario_key": scenario_key,
        "label": label,
        "description": description,
        "weighted_meroq_score": weighted_meroq_score,
        "portfolio_grade": score_to_grade(weighted_meroq_score),
        "portfolio_grade_label": grade_label(score_to_grade(weighted_meroq_score)),
        "weighted_up_probability": _weighted_sum(holdings, "final_up_probability", normalized),
        "weighted_downside_probability": _weighted_sum(holdings, "risk_loss_gt_5pct", normalized),
        "weighted_sentiment_score": _weighted_sum(holdings, "sentiment_score", normalized),
        "high_risk_weight": _weighted_risk_share(holdings, normalized),
        "largest_position_ticker": largest_ticker,
        "largest_position_weight": largest_weight,
        "concentration_score": concentration_score,
        "concentration_label": concentration_label,
    }
    return {key: _json_safe(value) for key, value in scenario.items()}


def _research_weight_series(holdings: pd.DataFrame) -> pd.Series:
    if holdings is None or holdings.empty:
        return pd.Series(dtype=float)

    score = _numeric_series(holdings, "meroq_score", default=50.0).clip(lower=0, upper=100) / 100.0
    up_probability = _numeric_series(holdings, "final_up_probability", default=0.5).clip(lower=0, upper=1)
    sentiment = _numeric_series(holdings, "sentiment_score", default=0.0).clip(lower=-1, upper=1)
    sentiment_component = (sentiment + 1.0) / 2.0
    downside = _numeric_series(holdings, "risk_loss_gt_5pct", default=0.25).clip(lower=0, upper=1)

    raw = 0.06 + (score * 0.58) + (up_probability * 0.23) + (sentiment_component * 0.13) - (downside * 0.42)

    if "risk_label" in holdings:
        high_risk = holdings["risk_label"].astype(str).str.contains("High|Elevated", case=False, na=False)
        raw.loc[high_risk] = raw.loc[high_risk] * 0.72
    raw.loc[score < 0.42] = raw.loc[score < 0.42] * 0.72
    raw.loc[score >= 0.70] = raw.loc[score >= 0.70] * 1.08

    raw = raw.clip(lower=0.025)
    return _cap_and_redistribute(_normalize_weight_series(raw), cap=0.28)


def _normalize_weight_series(values: pd.Series) -> pd.Series:
    series = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(lower=0.0)
    total = float(series.sum())
    if total <= 0 and len(series):
        return pd.Series([1.0 / len(series)] * len(series), index=series.index)
    if total <= 0:
        return series
    return series / total


def _cap_and_redistribute(weights: pd.Series, cap: float = 0.28, max_iter: int = 12) -> pd.Series:
    capped = _normalize_weight_series(weights).copy()
    if capped.empty or cap <= 0:
        return capped

    for _ in range(max_iter):
        over = capped > cap
        if not bool(over.any()):
            break
        excess = float((capped.loc[over] - cap).sum())
        capped.loc[over] = cap
        under = capped < cap
        under_total = float(capped.loc[under].sum())
        if excess <= 0 or under_total <= 0:
            break
        capped.loc[under] = capped.loc[under] + (capped.loc[under] / under_total) * excess

    return _normalize_weight_series(capped)


def _numeric_series(holdings: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in holdings:
        return pd.Series([default] * len(holdings), index=holdings.index, dtype=float)
    return pd.to_numeric(holdings[column], errors="coerce").fillna(default).astype(float)


def _weighted_sum(holdings: pd.DataFrame, column: str, weights: pd.Series) -> float:
    if column not in holdings:
        return 0.0
    values = _numeric_series(holdings, column)
    aligned = weights.reindex(holdings.index).fillna(0.0)
    return float((values * aligned).sum())


def _weighted_risk_share(holdings: pd.DataFrame, weights: pd.Series) -> float:
    if "risk_label" not in holdings:
        return 0.0
    mask = holdings["risk_label"].astype(str).str.contains("High|Elevated", case=False, na=False)
    return float(weights.reindex(holdings.index).fillna(0.0).loc[mask].sum())


def _scenario_summary(scenario: dict[str, Any]) -> str:
    score_delta = float(scenario.get("score_delta", 0.0) or 0.0)
    downside_delta = float(scenario.get("downside_delta", 0.0) or 0.0)
    concentration = scenario.get("concentration_label", "Unknown")
    if scenario.get("scenario_key") == "current":
        return "Baseline view using the weights entered for this scan."

    score_word = "raises" if score_delta >= 0 else "lowers"
    downside_word = "lowers" if downside_delta <= 0 else "raises"
    return (
        f"This scenario {score_word} weighted Meroq Score by {abs(score_delta):.1f} points "
        f"and {downside_word} weighted downside probability by {abs(downside_delta):.1%}; "
        f"concentration reads {str(concentration).lower()}."
    )


def _allocation_review_note(row: pd.Series) -> str:
    delta = _safe_float(row.get("research_weight_delta"))
    score = _safe_float(row.get("meroq_score"), 50.0)
    downside = _safe_float(row.get("risk_loss_gt_5pct"))
    if delta >= 0.035:
        return "Research scenario adds weight"
    if delta <= -0.035:
        return "Research scenario trims weight"
    if score < 42 and downside >= 0.32:
        return "Weak/high-risk holding to review"
    return "Near current scenario weight"


def _holding_exposure_note(row: pd.Series) -> str:
    parts: list[str] = []
    weight = _safe_float(row.get("weight"))
    score = _safe_float(row.get("meroq_score"), 50.0)
    downside = _safe_float(row.get("risk_loss_gt_5pct"))
    sentiment = str(row.get("sentiment_label", "")).lower()
    if weight >= 0.25:
        parts.append("large allocation")
    if downside >= 0.32:
        parts.append("downside driver")
    if score < 42:
        parts.append("weak score")
    elif score >= 70:
        parts.append("score support")
    if "negative" in sentiment or "caution" in sentiment:
        parts.append("news caution")
    return ", ".join(parts) if parts else "balanced contributor"


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        v = float(value)
        return v if np.isfinite(v) else None
    return value
