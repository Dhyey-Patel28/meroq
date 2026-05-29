from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SimulationSettings:
    horizon: int
    n_paths: int
    volatility_window: int
    drift_mode: str
    random_seed: int


def _to_numeric_close(df: pd.DataFrame) -> pd.Series:
    if "Close" not in df.columns:
        raise ValueError("Price data must include a Close column for risk simulation.")
    close = pd.to_numeric(df["Close"], errors="coerce").dropna()
    if len(close) < 30:
        raise ValueError("Not enough close price data for Monte Carlo simulation. Try a longer history period.")
    return close.reset_index(drop=True)


def estimate_return_parameters(
    price_df: pd.DataFrame,
    volatility_window: int = 60,
    drift_mode: str = "historical_mean",
    model_up_probability: float | None = None,
) -> dict:
    """Estimate per-period return and volatility inputs for simulation.

    The model-adjusted option uses the ML probability only as a conservative tilt,
    not as a claim of certainty. This keeps the simulation explainable and avoids
    overfitting the path generator to one classifier output.
    """
    close = _to_numeric_close(price_df)
    log_returns = np.log(close / close.shift(1)).replace([np.inf, -np.inf], np.nan).dropna()

    if log_returns.empty:
        raise ValueError("Could not calculate returns for risk simulation.")

    window = max(5, min(int(volatility_window), len(log_returns)))
    recent_returns = log_returns.tail(window)

    historical_mean = float(log_returns.mean())
    recent_mean = float(recent_returns.mean())
    recent_volatility = float(recent_returns.std(ddof=1))

    if not np.isfinite(recent_volatility) or recent_volatility <= 0:
        recent_volatility = float(log_returns.std(ddof=1))

    if not np.isfinite(recent_volatility) or recent_volatility <= 0:
        raise ValueError("Could not estimate a positive volatility for risk simulation.")

    mode = drift_mode.lower().strip()
    if mode == "zero_drift":
        drift = 0.0
    elif mode == "recent_mean":
        drift = recent_mean
    elif mode == "model_adjusted" and model_up_probability is not None:
        # Conservative tilt based on directional probability. The 0.25 multiplier
        # prevents one model probability from dominating realized volatility.
        probability_tilt = (float(model_up_probability) - 0.5) * recent_volatility * 0.25
        drift = historical_mean + probability_tilt
    else:
        drift = historical_mean

    return {
        "drift": float(drift),
        "historical_mean": float(historical_mean),
        "recent_mean": float(recent_mean),
        "volatility": float(recent_volatility),
        "volatility_window": int(window),
        "drift_mode": mode,
        "latest_price": float(close.iloc[-1]),
        "returns_used": int(len(log_returns)),
    }


def simulate_price_paths(
    price_df: pd.DataFrame,
    horizon: int = 30,
    n_paths: int = 1000,
    volatility_window: int = 60,
    drift_mode: str = "historical_mean",
    model_up_probability: float | None = None,
    random_seed: int = 42,
) -> dict:
    """Simulate future price paths using geometric Brownian motion."""
    horizon = int(horizon)
    n_paths = int(n_paths)
    if horizon < 1:
        raise ValueError("Simulation horizon must be at least 1 period.")
    if n_paths < 100:
        raise ValueError("Number of simulation paths must be at least 100.")

    params = estimate_return_parameters(
        price_df=price_df,
        volatility_window=volatility_window,
        drift_mode=drift_mode,
        model_up_probability=model_up_probability,
    )

    rng = np.random.default_rng(int(random_seed))
    shocks = rng.normal(loc=0.0, scale=1.0, size=(horizon, n_paths))

    # GBM log-return form. With per-period log-return drift and volatility,
    # the simulated price evolves as S_t = S_0 * exp(cumulative log returns).
    simulated_log_returns = (params["drift"] - 0.5 * params["volatility"] ** 2) + params["volatility"] * shocks
    cumulative_log_returns = np.cumsum(simulated_log_returns, axis=0)
    paths = params["latest_price"] * np.exp(cumulative_log_returns)

    path_df = pd.DataFrame(paths)
    path_df.insert(0, "step", np.arange(1, horizon + 1))

    percentiles = pd.DataFrame(
        {
            "step": np.arange(1, horizon + 1),
            "p05": np.percentile(paths, 5, axis=1),
            "p10": np.percentile(paths, 10, axis=1),
            "p25": np.percentile(paths, 25, axis=1),
            "p50": np.percentile(paths, 50, axis=1),
            "p75": np.percentile(paths, 75, axis=1),
            "p90": np.percentile(paths, 90, axis=1),
            "p95": np.percentile(paths, 95, axis=1),
        }
    )

    final_prices = paths[-1, :]
    final_returns = final_prices / params["latest_price"] - 1.0

    # Path-level max drawdown from current price baseline.
    full_paths = np.vstack([np.full((1, n_paths), params["latest_price"]), paths])
    running_max = np.maximum.accumulate(full_paths, axis=0)
    drawdowns = full_paths / running_max - 1.0
    max_drawdowns = drawdowns.min(axis=0)

    summary = {
        "current_price": params["latest_price"],
        "horizon": horizon,
        "n_paths": n_paths,
        "drift_mode": params["drift_mode"],
        "period_drift": params["drift"],
        "period_volatility": params["volatility"],
        "volatility_window": params["volatility_window"],
        "expected_final_price": float(np.mean(final_prices)),
        "median_final_price": float(np.percentile(final_prices, 50)),
        "p10_final_price": float(np.percentile(final_prices, 10)),
        "p90_final_price": float(np.percentile(final_prices, 90)),
        "expected_return": float(np.mean(final_returns)),
        "median_return": float(np.percentile(final_returns, 50)),
        "p10_return": float(np.percentile(final_returns, 10)),
        "p90_return": float(np.percentile(final_returns, 90)),
        "probability_positive_return": float(np.mean(final_returns > 0)),
        "probability_loss_gt_5pct": float(np.mean(final_returns <= -0.05)),
        "probability_gain_gt_5pct": float(np.mean(final_returns >= 0.05)),
        "expected_max_drawdown": float(np.mean(max_drawdowns)),
        "p10_max_drawdown": float(np.percentile(max_drawdowns, 10)),
        "p50_max_drawdown": float(np.percentile(max_drawdowns, 50)),
        "p90_max_drawdown": float(np.percentile(max_drawdowns, 90)),
    }

    final_distribution = pd.DataFrame(
        {
            "final_price": final_prices,
            "final_return": final_returns,
            "max_drawdown": max_drawdowns,
        }
    )

    return {
        "summary": summary,
        "percentiles": percentiles,
        "paths": path_df,
        "final_distribution": final_distribution,
        "parameters": params,
    }


def risk_label(summary: dict) -> str:
    """Create a simple human-readable risk label from simulation output."""
    downside = float(summary.get("probability_loss_gt_5pct", 0.0))
    positive = float(summary.get("probability_positive_return", 0.0))

    if downside >= 0.35:
        return "High downside risk"
    if positive >= 0.60 and downside <= 0.20:
        return "Constructive risk profile"
    if positive <= 0.45:
        return "Cautious risk profile"
    return "Balanced risk profile"
