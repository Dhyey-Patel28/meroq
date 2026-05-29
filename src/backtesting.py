from __future__ import annotations

import math
from typing import Callable, Iterable

import numpy as np
import pandas as pd

from src.model import (
    FEATURE_COLUMNS,
    MODEL_LABELS,
    classification_metrics,
    force_numeric_features,
    make_classifier,
)


def _max_drawdown(equity_curve: pd.Series) -> float:
    """Return max drawdown as a negative percentage value."""
    if equity_curve.empty:
        return np.nan
    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1
    return float(drawdown.min())


def _safe_annualized_return(total_return: float, periods: int, periods_per_year: int) -> float:
    if periods <= 0 or total_return <= -1:
        return np.nan
    years = periods / periods_per_year
    if years <= 0:
        return np.nan
    return float((1 + total_return) ** (1 / years) - 1)


def _strategy_metrics(
    returns: pd.Series,
    market_returns: pd.Series,
    positions: pd.Series,
    periods_per_year: int,
) -> dict:
    """Compute trading/backtesting metrics."""
    returns = pd.to_numeric(returns, errors="coerce").fillna(0.0)
    market_returns = pd.to_numeric(market_returns, errors="coerce").fillna(0.0)
    positions = pd.to_numeric(positions, errors="coerce").fillna(0.0)

    strategy_equity = (1 + returns).cumprod()
    market_equity = (1 + market_returns).cumprod()

    total_return = float(strategy_equity.iloc[-1] - 1) if len(strategy_equity) else np.nan
    buy_hold_return = float(market_equity.iloc[-1] - 1) if len(market_equity) else np.nan
    annualized_return = _safe_annualized_return(total_return, len(returns), periods_per_year)

    std = returns.std(ddof=0)
    vol = float(std * math.sqrt(periods_per_year)) if len(returns) else np.nan
    sharpe = float((returns.mean() / std) * math.sqrt(periods_per_year)) if std > 0 else np.nan
    max_drawdown = _max_drawdown(strategy_equity)

    active_returns = returns[positions != 0]
    win_rate = float((active_returns > 0).mean()) if len(active_returns) else np.nan
    exposure = float((positions != 0).mean()) if len(positions) else np.nan
    trades = int((positions.diff().abs().fillna(positions.abs()) > 0).sum())

    return {
        "strategy_total_return": total_return,
        "buy_hold_return": buy_hold_return,
        "annualized_return": annualized_return,
        "annualized_volatility": vol,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "exposure": exposure,
        "trades": trades,
    }


def _predict_up_probability(model, X: pd.DataFrame) -> np.ndarray:
    """Return P(up) from any supported classifier."""
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(X)
        if probabilities.ndim == 2 and probabilities.shape[1] >= 2:
            return probabilities[:, 1].astype(float)

    if hasattr(model, "decision_function"):
        scores = model.decision_function(X)
        return (1 / (1 + np.exp(-scores))).astype(float)

    pred = model.predict(X)
    return np.where(pred == 1, 0.55, 0.45).astype(float)


def walk_forward_backtest(
    model_frame: pd.DataFrame,
    initial_train_size: int,
    test_size: int,
    step_size: int,
    probability_threshold: float = 0.55,
    transaction_cost_bps: float = 10.0,
    periods_per_year: int = 252,
    max_folds: int = 30,
    n_estimators: int = 150,
    model_name: str = "xgboost",
    progress_callback: Callable[[dict], None] | None = None,
) -> dict:
    """
    Run expanding-window walk-forward validation for one model.

    For each fold:
    - train on all rows up to the fold boundary
    - predict the next future test window
    - move forward by step_size

    Strategy logic:
    - Long-only position = 1 when predicted up probability >= threshold, else 0
    - Long-short position = 1 when probability >= threshold, -1 when probability <= 1-threshold, else 0
    - Returns use next_return, so a signal at row t is evaluated on t -> t+1 movement
    """
    data = force_numeric_features(model_frame)
    data = data.dropna(subset=["Date", "Close", "next_return"]).reset_index(drop=True)

    min_needed = initial_train_size + test_size
    if len(data) < min_needed:
        raise ValueError(
            f"Not enough rows for walk-forward backtest. Need at least {min_needed}, got {len(data)}. "
            "Try 10y or max history, especially for weekly interval."
        )

    if model_name not in MODEL_LABELS:
        raise ValueError(f"Unknown model_name '{model_name}'. Choose from: {list(MODEL_LABELS)}")

    fold_starts = list(range(initial_train_size, len(data) - test_size + 1, step_size))
    if max_folds and len(fold_starts) > max_folds:
        # Keep recent folds to keep the app responsive.
        fold_starts = fold_starts[-max_folds:]

    prediction_frames: list[pd.DataFrame] = []
    fold_rows: list[dict] = []

    total_folds = len(fold_starts)

    for fold_number, start in enumerate(fold_starts, start=1):
        train = data.iloc[:start].copy()
        test = data.iloc[start : start + test_size].copy()

        if progress_callback is not None:
            progress_callback(
                {
                    "phase": "walk_forward",
                    "status": "running",
                    "model_name": model_name,
                    "model": MODEL_LABELS[model_name],
                    "fold": fold_number,
                    "total_folds": total_folds,
                    "train_rows": len(train),
                    "test_rows": len(test),
                    "train_end": train["Date"].iloc[-1],
                    "test_start": test["Date"].iloc[0],
                    "test_end": test["Date"].iloc[-1],
                }
            )

        X_train = train[FEATURE_COLUMNS].astype("float64")
        y_train = train["target_up_tomorrow"].astype("int64")
        X_test = test[FEATURE_COLUMNS].astype("float64")

        model = make_classifier(model_name=model_name, n_estimators=n_estimators)
        model.fit(X_train, y_train)

        test = test.copy()
        test["fold"] = fold_number
        test["model_name"] = model_name
        test["model"] = MODEL_LABELS[model_name]
        test["proba_up"] = _predict_up_probability(model, X_test)
        test["pred_up"] = (test["proba_up"] >= 0.5).astype(int)
        prediction_frames.append(test)

        if progress_callback is not None:
            progress_callback(
                {
                    "phase": "walk_forward",
                    "status": "complete",
                    "model_name": model_name,
                    "model": MODEL_LABELS[model_name],
                    "fold": fold_number,
                    "total_folds": total_folds,
                    "avg_proba_up": float(pd.Series(test["proba_up"]).mean()),
                    "predicted_up_rate": float(pd.Series(test["pred_up"]).mean()),
                }
            )

        fold_rows.append(
            {
                "fold": fold_number,
                "model_name": model_name,
                "model": MODEL_LABELS[model_name],
                "train_start": train["Date"].iloc[0],
                "train_end": train["Date"].iloc[-1],
                "test_start": test["Date"].iloc[0],
                "test_end": test["Date"].iloc[-1],
                "train_rows": len(train),
                "test_rows": len(test),
            }
        )

    predictions = pd.concat(prediction_frames, ignore_index=True)
    predictions = predictions.sort_values("Date").drop_duplicates(subset=["Date", "model_name"], keep="last")
    predictions = predictions.reset_index(drop=True)

    predictions["market_return"] = pd.to_numeric(predictions["next_return"], errors="coerce").fillna(0.0)

    long_position = (predictions["proba_up"] >= probability_threshold).astype(float)
    long_short_position = np.select(
        [
            predictions["proba_up"] >= probability_threshold,
            predictions["proba_up"] <= (1 - probability_threshold),
        ],
        [1.0, -1.0],
        default=0.0,
    )

    cost = transaction_cost_bps / 10_000

    predictions["long_position"] = long_position
    predictions["long_turnover"] = predictions["long_position"].diff().abs().fillna(predictions["long_position"].abs())
    predictions["long_strategy_return"] = (
        predictions["long_position"] * predictions["market_return"] - predictions["long_turnover"] * cost
    )

    predictions["long_short_position"] = long_short_position
    predictions["long_short_turnover"] = predictions["long_short_position"].diff().abs().fillna(
        predictions["long_short_position"].abs()
    )
    predictions["long_short_strategy_return"] = (
        predictions["long_short_position"] * predictions["market_return"]
        - predictions["long_short_turnover"] * cost
    )

    predictions["market_equity"] = (1 + predictions["market_return"]).cumprod()
    predictions["long_equity"] = (1 + predictions["long_strategy_return"]).cumprod()
    predictions["long_short_equity"] = (1 + predictions["long_short_strategy_return"]).cumprod()

    y_true = predictions["target_up_tomorrow"].astype("int64")
    y_pred = predictions["pred_up"].astype("int64")
    y_proba = predictions["proba_up"].astype("float64")

    class_metrics = classification_metrics(y_true, y_pred, y_proba)

    long_metrics = _strategy_metrics(
        predictions["long_strategy_return"],
        predictions["market_return"],
        predictions["long_position"],
        periods_per_year,
    )
    long_short_metrics = _strategy_metrics(
        predictions["long_short_strategy_return"],
        predictions["market_return"],
        predictions["long_short_position"],
        periods_per_year,
    )

    return {
        "model_name": model_name,
        "model_label": MODEL_LABELS[model_name],
        "predictions": predictions,
        "folds": pd.DataFrame(fold_rows),
        "classification_metrics": class_metrics,
        "long_metrics": long_metrics,
        "long_short_metrics": long_short_metrics,
        "settings": {
            "model_name": model_name,
            "model": MODEL_LABELS[model_name],
            "initial_train_size": initial_train_size,
            "test_size": test_size,
            "step_size": step_size,
            "probability_threshold": probability_threshold,
            "transaction_cost_bps": transaction_cost_bps,
            "periods_per_year": periods_per_year,
            "folds": len(fold_rows),
        },
    }


def summarize_walk_forward_result(result: dict) -> dict:
    """Flatten one walk-forward result into a comparison row."""
    c = result["classification_metrics"]
    long = result["long_metrics"]
    long_short = result["long_short_metrics"]
    settings = result["settings"]

    return {
        "model_name": result["model_name"],
        "model": result["model_label"],
        "folds": settings["folds"],
        "accuracy": c["accuracy"],
        "precision": c["precision"],
        "recall": c["recall"],
        "f1": c["f1"],
        "roc_auc": c["roc_auc"],
        "long_total_return": long["strategy_total_return"],
        "long_sharpe": long["sharpe_ratio"],
        "long_max_drawdown": long["max_drawdown"],
        "long_trades": long["trades"],
        "long_short_total_return": long_short["strategy_total_return"],
        "long_short_sharpe": long_short["sharpe_ratio"],
        "long_short_max_drawdown": long_short["max_drawdown"],
    }


def compare_models_walk_forward(
    model_frame: pd.DataFrame,
    model_names: Iterable[str],
    initial_train_size: int,
    test_size: int,
    step_size: int,
    probability_threshold: float = 0.55,
    transaction_cost_bps: float = 10.0,
    periods_per_year: int = 252,
    max_folds: int = 15,
    n_estimators: int = 120,
    progress_callback: Callable[[dict], None] | None = None,
) -> tuple[pd.DataFrame, dict[str, dict]]:
    """Run walk-forward backtests for multiple model families."""
    model_names = list(model_names)
    rows: list[dict] = []
    results: dict[str, dict] = {}
    total_models = len(model_names)

    for model_index, model_name in enumerate(model_names, start=1):
        if progress_callback is not None:
            progress_callback(
                {
                    "phase": "walk_forward_model_comparison",
                    "status": "running",
                    "model_name": model_name,
                    "model": MODEL_LABELS.get(model_name, model_name),
                    "model_index": model_index,
                    "model_total": total_models,
                }
            )

        def _child_progress(payload: dict) -> None:
            if progress_callback is not None:
                enriched = dict(payload)
                enriched["phase"] = "walk_forward_model_comparison"
                enriched["model_index"] = model_index
                enriched["model_total"] = total_models
                progress_callback(enriched)

        try:
            result = walk_forward_backtest(
                model_frame=model_frame,
                initial_train_size=initial_train_size,
                test_size=test_size,
                step_size=step_size,
                probability_threshold=probability_threshold,
                transaction_cost_bps=transaction_cost_bps,
                periods_per_year=periods_per_year,
                max_folds=max_folds,
                n_estimators=n_estimators,
                model_name=model_name,
                progress_callback=_child_progress,
            )
            rows.append({**summarize_walk_forward_result(result), "status": "ok"})
            results[model_name] = result

            if progress_callback is not None:
                progress_callback(
                    {
                        "phase": "walk_forward_model_comparison",
                        "status": "complete",
                        "model_name": model_name,
                        "model": MODEL_LABELS.get(model_name, model_name),
                        "model_index": model_index,
                        "model_total": total_models,
                    }
                )
        except Exception as exc:
            if progress_callback is not None:
                progress_callback(
                    {
                        "phase": "walk_forward_model_comparison",
                        "status": "failed",
                        "model_name": model_name,
                        "model": MODEL_LABELS.get(model_name, model_name),
                        "model_index": model_index,
                        "model_total": total_models,
                        "error": str(exc),
                    }
                )

            rows.append(
                {
                    "model_name": model_name,
                    "model": MODEL_LABELS.get(model_name, model_name),
                    "folds": np.nan,
                    "accuracy": np.nan,
                    "precision": np.nan,
                    "recall": np.nan,
                    "f1": np.nan,
                    "roc_auc": np.nan,
                    "long_total_return": np.nan,
                    "long_sharpe": np.nan,
                    "long_max_drawdown": np.nan,
                    "long_trades": np.nan,
                    "long_short_total_return": np.nan,
                    "long_short_sharpe": np.nan,
                    "long_short_max_drawdown": np.nan,
                    "status": f"failed: {exc}",
                }
            )

    summary = pd.DataFrame(rows)
    if not summary.empty:
        summary = summary.sort_values(["roc_auc", "long_sharpe", "accuracy"], ascending=False, na_position="last")
    return summary.reset_index(drop=True), results
