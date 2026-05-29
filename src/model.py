from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
    StackingClassifier,
    VotingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

try:  # Optional dependency installed through requirements.txt in Stage 3.5.
    from lightgbm import LGBMClassifier
except Exception:  # pragma: no cover - keeps the app usable if the wheel fails locally.
    LGBMClassifier = None

try:  # Optional dependency installed through requirements.txt in Stage 3.5.
    from catboost import CatBoostClassifier
except Exception:  # pragma: no cover - keeps the app usable if the wheel fails locally.
    CatBoostClassifier = None


FEATURE_COLUMNS = [
    "return_1d",
    "log_return_1d",
    "intraday_return",
    "high_low_range",
    "volume_change",
    "sma_5",
    "sma_10",
    "sma_20",
    "sma_50",
    "ema_12",
    "ema_26",
    "close_sma20_ratio",
    "close_sma50_ratio",
    "volatility_5",
    "volatility_10",
    "volatility_20",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_diff",
    "bb_width",
    "bb_position",
    "atr_pct",
    "stoch_k",
    "stoch_d",
]


MODEL_LABELS = {
    "momentum_baseline": "Momentum Baseline",
    "logistic_regression": "Logistic Regression",
    "random_forest": "Random Forest",
    "extra_trees": "Extra Trees",
    "hist_gradient_boosting": "HistGradientBoosting",
    "xgboost": "XGBoost",
    "lightgbm": "LightGBM",
    "catboost": "CatBoost",
    "soft_voting_ensemble": "Soft Voting Ensemble",
    "stacking_ensemble": "Stacking Ensemble",
}

MODEL_NAMES = list(MODEL_LABELS.keys())
DEFAULT_MODEL_NAME = "xgboost"

# Keep UI experiments responsive. More serious tuning will come later.
TREE_MODEL_NAMES = {
    "random_forest",
    "extra_trees",
    "xgboost",
    "lightgbm",
    "catboost",
}
ENSEMBLE_MODEL_NAMES = {"soft_voting_ensemble", "stacking_ensemble"}


class MomentumBaselineClassifier(BaseEstimator, ClassifierMixin):
    """
    Simple benchmark model.

    If the latest return is positive, it leans bullish; if negative, it leans
    bearish. This is intentionally basic so advanced models have a transparent
    baseline to beat.
    """

    def __init__(self, bullish_probability: float = 0.55, bearish_probability: float = 0.45):
        self.bullish_probability = bullish_probability
        self.bearish_probability = bearish_probability
        self.classes_ = np.array([0, 1])

    def fit(self, X, y=None):
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X):
        X_df = pd.DataFrame(X, columns=getattr(X, "columns", None))
        if "return_1d" in X_df.columns:
            momentum = pd.to_numeric(X_df["return_1d"], errors="coerce").fillna(0.0)
        else:
            momentum = pd.Series(np.zeros(len(X_df)), index=X_df.index)

        p_up = np.where(momentum > 0, self.bullish_probability, self.bearish_probability).astype(float)
        return np.column_stack([1 - p_up, p_up])

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)


@dataclass(frozen=True)
class ModelSpec:
    name: str
    label: str
    family: str
    supports_feature_importance: bool = False
    is_optional_dependency: bool = False


def model_dependency_status() -> pd.DataFrame:
    """Return dependency availability for the advanced model suite."""
    rows = []
    for name, label in MODEL_LABELS.items():
        if name == "lightgbm":
            available = LGBMClassifier is not None
            dependency = "lightgbm"
        elif name == "catboost":
            available = CatBoostClassifier is not None
            dependency = "catboost"
        elif name in ENSEMBLE_MODEL_NAMES:
            # Ensembles are usable without CatBoost/LightGBM because they fall
            # back to the installed base models. They get stronger when both are installed.
            available = True
            dependency = "uses installed base models"
        else:
            available = True
            dependency = "built-in / installed"

        rows.append(
            {
                "model_name": name,
                "model": label,
                "dependency": dependency,
                "available": available,
            }
        )
    return pd.DataFrame(rows)


def get_model_spec(model_name: str) -> ModelSpec:
    """Return model metadata for a known model name."""
    if model_name not in MODEL_LABELS:
        raise ValueError(f"Unknown model_name '{model_name}'. Choose from: {list(MODEL_LABELS)}")

    family = "baseline"
    if model_name == "logistic_regression":
        family = "linear"
    elif model_name in {"random_forest", "extra_trees"}:
        family = "bagging/tree ensemble"
    elif model_name in {"hist_gradient_boosting", "xgboost", "lightgbm", "catboost"}:
        family = "boosting"
    elif model_name in ENSEMBLE_MODEL_NAMES:
        family = "ensemble"

    return ModelSpec(
        name=model_name,
        label=MODEL_LABELS[model_name],
        family=family,
        supports_feature_importance=model_name
        in {
            "logistic_regression",
            "random_forest",
            "extra_trees",
            "xgboost",
            "lightgbm",
            "catboost",
        },
        is_optional_dependency=model_name in {"lightgbm", "catboost"},
    )


def make_xgboost_classifier(n_estimators: int = 300) -> XGBClassifier:
    """Create the standard Meroq XGBoost classifier."""
    return XGBClassifier(
        n_estimators=n_estimators,
        learning_rate=0.03,
        max_depth=3,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        reg_lambda=1.0,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=42,
        n_jobs=1,
        verbosity=0,
    )


def make_lightgbm_classifier(n_estimators: int = 300):
    """Create a LightGBM classifier, or raise a clear install error."""
    if LGBMClassifier is None:
        raise ImportError("LightGBM is not installed. Run: python -m pip install lightgbm")

    return LGBMClassifier(
        n_estimators=n_estimators,
        learning_rate=0.03,
        max_depth=-1,
        num_leaves=15,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=1,
        verbose=-1,
    )


def make_catboost_classifier(n_estimators: int = 300):
    """Create a CatBoost classifier, or raise a clear install error."""
    if CatBoostClassifier is None:
        raise ImportError("CatBoost is not installed. Run: python -m pip install catboost")

    return CatBoostClassifier(
        iterations=n_estimators,
        learning_rate=0.03,
        depth=4,
        loss_function="Logloss",
        eval_metric="AUC",
        random_seed=42,
        verbose=False,
        allow_writing_files=False,
    )


def make_logistic_pipeline() -> Pipeline:
    """Create standardized logistic regression model."""
    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )


def _ensemble_estimators(n_estimators: int = 120) -> list[tuple[str, object]]:
    """Return installed base estimators for voting/stacking ensembles."""
    light_n = max(30, int(n_estimators * 0.75))
    cat_n = max(30, int(n_estimators * 0.75))

    estimators: list[tuple[str, object]] = [
        ("lr", make_logistic_pipeline()),
        (
            "rf",
            RandomForestClassifier(
                n_estimators=n_estimators,
                max_depth=6,
                min_samples_leaf=10,
                class_weight="balanced_subsample",
                random_state=42,
                n_jobs=-1,
            ),
        ),
        (
            "et",
            ExtraTreesClassifier(
                n_estimators=n_estimators,
                max_depth=6,
                min_samples_leaf=10,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            ),
        ),
        ("xgb", make_xgboost_classifier(n_estimators=n_estimators)),
    ]

    if LGBMClassifier is not None:
        estimators.append(("lgbm", make_lightgbm_classifier(n_estimators=light_n)))
    if CatBoostClassifier is not None:
        estimators.append(("cat", make_catboost_classifier(n_estimators=cat_n)))

    return estimators


def make_classifier(model_name: str = DEFAULT_MODEL_NAME, n_estimators: int = 300):
    """Create a classifier by name."""
    model_name = model_name or DEFAULT_MODEL_NAME

    if model_name == "momentum_baseline":
        return MomentumBaselineClassifier()

    if model_name == "logistic_regression":
        return make_logistic_pipeline()

    if model_name == "random_forest":
        return RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=6,
            min_samples_leaf=10,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        )

    if model_name == "extra_trees":
        return ExtraTreesClassifier(
            n_estimators=n_estimators,
            max_depth=6,
            min_samples_leaf=10,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )

    if model_name == "hist_gradient_boosting":
        return HistGradientBoostingClassifier(
            max_iter=n_estimators,
            learning_rate=0.03,
            max_leaf_nodes=15,
            l2_regularization=0.05,
            early_stopping=True,
            random_state=42,
        )

    if model_name == "xgboost":
        return make_xgboost_classifier(n_estimators=n_estimators)

    if model_name == "lightgbm":
        return make_lightgbm_classifier(n_estimators=n_estimators)

    if model_name == "catboost":
        return make_catboost_classifier(n_estimators=n_estimators)

    if model_name == "soft_voting_ensemble":
        return VotingClassifier(
            estimators=_ensemble_estimators(n_estimators=max(40, min(n_estimators, 120))),
            voting="soft",
            n_jobs=1,
        )

    if model_name == "stacking_ensemble":
        return StackingClassifier(
            estimators=_ensemble_estimators(n_estimators=max(40, min(n_estimators, 100))),
            final_estimator=LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42),
            stack_method="predict_proba",
            passthrough=False,
            cv=3,
            n_jobs=1,
        )

    raise ValueError(f"Unknown model_name '{model_name}'. Choose from: {list(MODEL_LABELS)}")


def force_numeric_features(df: pd.DataFrame) -> pd.DataFrame:
    """Force model feature columns to numeric floats for sklearn/XGBoost."""
    data = df.copy()

    for col in FEATURE_COLUMNS:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data["target_up_tomorrow"] = pd.to_numeric(data["target_up_tomorrow"], errors="coerce")

    if "next_return" in data.columns:
        data["next_return"] = pd.to_numeric(data["next_return"], errors="coerce")
    if "Close" in data.columns:
        data["Close"] = pd.to_numeric(data["Close"], errors="coerce")
    if "Date" in data.columns:
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")

    required = FEATURE_COLUMNS + ["target_up_tomorrow"]
    data = data.replace([np.inf, -np.inf], np.nan)
    data = data.dropna(subset=required).reset_index(drop=True)
    return data


def classification_metrics(y_true, y_pred, y_proba) -> dict:
    """Return common binary classification metrics."""
    y_true = pd.Series(y_true).astype(int)
    y_pred = pd.Series(y_pred).astype(int)
    y_proba = pd.Series(y_proba).astype(float)

    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, y_proba) if len(np.unique(y_true)) > 1 else np.nan,
    }


def _predict_up_probability(model, X: pd.DataFrame) -> np.ndarray:
    """Return P(up) from any supported classifier."""
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(X)
        if probabilities.ndim == 2 and probabilities.shape[1] >= 2:
            return probabilities[:, 1].astype(float)

    # Fallback for classifiers with decision_function only.
    if hasattr(model, "decision_function"):
        scores = model.decision_function(X)
        return (1 / (1 + np.exp(-scores))).astype(float)

    # Last resort: convert hard predictions to weak probabilities.
    pred = model.predict(X)
    return np.where(pred == 1, 0.55, 0.45).astype(float)


def _feature_importance(model, model_name: str) -> pd.DataFrame:
    """Return a comparable feature importance table when available."""
    values = np.zeros(len(FEATURE_COLUMNS))

    if model_name in {"xgboost", "random_forest", "extra_trees", "lightgbm", "catboost"} and hasattr(
        model, "feature_importances_"
    ):
        values = model.feature_importances_
    elif model_name == "logistic_regression" and isinstance(model, Pipeline):
        logistic_model = model.named_steps.get("model")
        if logistic_model is not None and hasattr(logistic_model, "coef_"):
            values = np.abs(logistic_model.coef_[0])

    values = np.asarray(values, dtype=float)
    if len(values) != len(FEATURE_COLUMNS):
        values = np.zeros(len(FEATURE_COLUMNS))

    return (
        pd.DataFrame({"feature": FEATURE_COLUMNS, "importance": values})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


def _suggest_n_estimators(model_name: str, requested: int) -> int:
    """Keep advanced comparisons responsive without hiding the stronger models."""
    if model_name == "momentum_baseline":
        return 1
    if model_name == "logistic_regression":
        return 1
    if model_name in ENSEMBLE_MODEL_NAMES:
        return max(40, min(requested, 120))
    if model_name in TREE_MODEL_NAMES or model_name == "hist_gradient_boosting":
        return max(60, min(requested, 180))
    return requested


def train_classifier(
    model_frame: pd.DataFrame,
    model_name: str = DEFAULT_MODEL_NAME,
    test_size: float = 0.2,
    min_rows: int = 120,
    n_estimators: int = 300,
) -> dict:
    """
    Train one classifier using a chronological train/test split.

    No shuffling is used because this is time-series data.
    """
    spec = get_model_spec(model_name)
    data = force_numeric_features(model_frame)

    if len(data) < min_rows:
        raise ValueError(
            f"Not enough usable rows after indicators. Need at least {min_rows}, got {len(data)}. "
            "Try a longer period like 5y, 10y, or max."
        )

    split_idx = int(len(data) * (1 - test_size))
    train = data.iloc[:split_idx].copy()
    test = data.iloc[split_idx:].copy()

    X_train = train[FEATURE_COLUMNS].astype("float64")
    y_train = train["target_up_tomorrow"].astype("int64")
    X_test = test[FEATURE_COLUMNS].astype("float64")
    y_test = test["target_up_tomorrow"].astype("int64")

    model = make_classifier(model_name=model_name, n_estimators=_suggest_n_estimators(model_name, n_estimators))
    model.fit(X_train, y_train)

    proba = _predict_up_probability(model, X_test)
    pred = (proba >= 0.5).astype(int)

    metrics = classification_metrics(y_test, pred, proba)
    metrics.update({"train_rows": len(train), "test_rows": len(test)})

    feature_importance = _feature_importance(model, model_name)

    return {
        "model": model,
        "model_name": spec.name,
        "model_label": spec.label,
        "model_family": spec.family,
        "metrics": metrics,
        "feature_importance": feature_importance,
        "test": test,
        "test_predictions": pred,
        "test_probabilities": proba,
    }


def train_xgboost_classifier(
    model_frame: pd.DataFrame,
    test_size: float = 0.2,
    min_rows: int = 120,
) -> dict:
    """Backward-compatible wrapper for the original XGBoost model."""
    return train_classifier(
        model_frame=model_frame,
        model_name="xgboost",
        test_size=test_size,
        min_rows=min_rows,
        n_estimators=300,
    )


def predict_latest(model, latest_feature_row: pd.Series) -> dict:
    """Predict next-trading-day/period direction from the latest feature row."""
    X_latest = latest_feature_row[FEATURE_COLUMNS].to_frame().T

    for col in FEATURE_COLUMNS:
        X_latest[col] = pd.to_numeric(X_latest[col], errors="coerce")

    X_latest = X_latest.astype("float64")

    if X_latest.isna().any().any():
        missing_cols = X_latest.columns[X_latest.isna().any()].tolist()
        raise ValueError(f"Latest row has missing numeric features: {missing_cols}")

    up_probability = float(_predict_up_probability(model, X_latest)[0])

    if up_probability >= 0.55:
        signal = "Bullish"
    elif up_probability <= 0.45:
        signal = "Bearish"
    else:
        signal = "Neutral"

    return {
        "up_probability": up_probability,
        "down_probability": 1 - up_probability,
        "signal": signal,
    }


def compare_models_simple_split(
    model_frame: pd.DataFrame,
    model_names: Iterable[str] | None = None,
    test_size: float = 0.2,
    min_rows: int = 120,
    progress_callback: Callable[[dict], None] | None = None,
) -> tuple[pd.DataFrame, dict[str, dict]]:
    """Train and evaluate multiple models on the same chronological split."""
    model_names = list(model_names or MODEL_NAMES)
    rows: list[dict] = []
    results_by_model: dict[str, dict] = {}
    total = len(model_names)

    for index, model_name in enumerate(model_names, start=1):
        n_estimators = _suggest_n_estimators(model_name, 100)
        spec = get_model_spec(model_name)

        if progress_callback is not None:
            progress_callback(
                {
                    "phase": "simple_model_comparison",
                    "status": "running",
                    "model_name": model_name,
                    "model": MODEL_LABELS.get(model_name, model_name),
                    "index": index,
                    "total": total,
                }
            )

        try:
            result = train_classifier(
                model_frame=model_frame,
                model_name=model_name,
                test_size=test_size,
                min_rows=min_rows,
                n_estimators=n_estimators,
            )
            metrics = result["metrics"]
            row = {
                "model_name": model_name,
                "model": MODEL_LABELS[model_name],
                "family": spec.family,
                "accuracy": metrics["accuracy"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "roc_auc": metrics["roc_auc"],
                "train_rows": metrics["train_rows"],
                "test_rows": metrics["test_rows"],
                "status": "ok",
            }
            rows.append(row)
            results_by_model[model_name] = result

            if progress_callback is not None:
                progress_callback(
                    {
                        "phase": "simple_model_comparison",
                        "status": "complete",
                        "model_name": model_name,
                        "model": MODEL_LABELS.get(model_name, model_name),
                        "index": index,
                        "total": total,
                        "metrics": metrics,
                    }
                )
        except Exception as exc:  # Keep comparison table useful even if one model fails.
            rows.append(
                {
                    "model_name": model_name,
                    "model": MODEL_LABELS.get(model_name, model_name),
                    "family": spec.family if model_name in MODEL_LABELS else "unknown",
                    "accuracy": np.nan,
                    "precision": np.nan,
                    "recall": np.nan,
                    "f1": np.nan,
                    "roc_auc": np.nan,
                    "train_rows": np.nan,
                    "test_rows": np.nan,
                    "status": f"failed: {exc}",
                }
            )

            if progress_callback is not None:
                progress_callback(
                    {
                        "phase": "simple_model_comparison",
                        "status": "failed",
                        "model_name": model_name,
                        "model": MODEL_LABELS.get(model_name, model_name),
                        "index": index,
                        "total": total,
                        "error": str(exc),
                    }
                )

    summary = pd.DataFrame(rows)
    if not summary.empty:
        summary = summary.sort_values(["roc_auc", "f1", "accuracy"], ascending=False, na_position="last")
    return summary.reset_index(drop=True), results_by_model
