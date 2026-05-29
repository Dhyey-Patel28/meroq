from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from src.backtesting import compare_models_walk_forward, walk_forward_backtest
from src.charts import (
    make_backtest_preview,
    make_drawdown_chart,
    make_equity_curve_chart,
    make_feature_importance_chart,
    make_model_metric_bar_chart,
    make_price_chart,
    make_monte_carlo_percentile_chart,
    make_monte_carlo_sample_paths_chart,
    make_final_return_distribution_chart,
    make_probability_backtest_chart,
    make_probability_gauge,
    make_walk_forward_model_return_chart,
)
from src.config import DEFAULT_WATCHLIST, SUGGESTED_INTERVALS, SUGGESTED_PERIODS, WALK_FORWARD_DEFAULTS
from src.data_loader import fetch_price_data, list_saved_price_tables
from src.features import add_technical_features, build_model_frame
from src.model import (
    MODEL_LABELS,
    MODEL_NAMES,
    compare_models_simple_split,
    model_dependency_status,
    predict_latest,
    train_classifier,
)
from src.risk_simulation import risk_label, simulate_price_paths


st.set_page_config(page_title="Meroq", page_icon="📈", layout="wide")

st.title("📈 Meroq")
st.caption("Predictive market intelligence with advanced model comparison, sentiment, risk, and signal modeling.")

CORE_MODEL_NAMES = ["momentum_baseline", "logistic_regression", "random_forest", "xgboost"]
ADVANCED_MODEL_NAMES = MODEL_NAMES
ENSEMBLE_MODEL_NAMES = {"soft_voting_ensemble", "stacking_ensemble"}

with st.sidebar:
    st.header("Settings")
    ticker = st.text_input("Ticker", value="AAPL").upper().strip()
    period = st.selectbox("History period", SUGGESTED_PERIODS, index=2)
    interval = st.selectbox("Interval", SUGGESTED_INTERVALS, index=0)

    analysis_mode = st.selectbox(
        "Analysis mode",
        options=["Fast mode", "Research mode", "Full analysis mode", "Custom"],
        index=0,
        key="analysis_mode_v42",
        help=(
            "Fast mode keeps the app responsive. Research mode adds the primary walk-forward backtest. "
            "Full analysis mode intentionally enables heavier comparisons. Custom lets you choose manually."
        ),
    )

    mode_settings = {
        "Fast mode": {
            "primary_model": "XGBoost",
            "comparison_set": "Core fast",
            "run_primary_wf": False,
            "run_wf_model_comparison": False,
            "max_folds": 6,
        },
        "Research mode": {
            "primary_model": "XGBoost",
            "comparison_set": "Core fast",
            "run_primary_wf": True,
            "run_wf_model_comparison": False,
            "max_folds": 8,
        },
        "Full analysis mode": {
            "primary_model": "XGBoost",
            "comparison_set": "Advanced all",
            "run_primary_wf": True,
            "run_wf_model_comparison": True,
            "max_folds": 8,
        },
        "Custom": {
            "primary_model": "XGBoost",
            "comparison_set": "Core fast",
            "run_primary_wf": False,
            "run_wf_model_comparison": False,
            "max_folds": 8,
        },
    }[analysis_mode]

    st.caption(
        {
            "Fast mode": "Recommended while building: XGBoost, Monte Carlo risk, no slow walk-forward loops by default.",
            "Research mode": "Adds the primary walk-forward backtest with a limited number of recent folds.",
            "Full analysis mode": "Runs advanced comparisons and can be slow. Use when you intentionally want a heavier research run.",
            "Custom": "Manual control of model, comparison, and backtesting settings.",
        }[analysis_mode]
    )

    st.divider()
    st.subheader("Risk simulation")
    run_risk_simulation = st.checkbox(
        "Run Monte Carlo risk simulation",
        value=True,
        key="run_risk_simulation_v42",
        help="Fast simulation that estimates future price ranges and downside risk from recent volatility.",
    )
    simulation_horizon = st.selectbox(
        "Simulation horizon",
        options=[10, 21, 30, 60, 90],
        index=2,
        key="simulation_horizon_v42",
        help="Number of future trading periods to simulate. For daily data, 21 is about one month.",
    )
    simulation_paths = st.selectbox(
        "Simulation paths",
        options=[500, 1000, 2500, 5000],
        index=1,
        key="simulation_paths_v42",
        help="More paths create smoother distributions but take slightly longer.",
    )
    volatility_window = st.selectbox(
        "Volatility window",
        options=[20, 60, 126, 252],
        index=1,
        key="volatility_window_v42",
        help="Recent periods used to estimate volatility for the simulation.",
    )
    drift_label_to_mode = {
        "Historical mean": "historical_mean",
        "Recent mean": "recent_mean",
        "Zero drift": "zero_drift",
        "Model-adjusted": "model_adjusted",
    }
    selected_drift_label = st.selectbox(
        "Drift assumption",
        options=list(drift_label_to_mode.keys()),
        index=3,
        key="drift_assumption_v42",
        help="Model-adjusted uses the ML probability as a conservative tilt, not as certainty.",
    )
    drift_mode = drift_label_to_mode[selected_drift_label]

    st.divider()
    st.subheader("Model")
    model_label_to_name = {label: name for name, label in MODEL_LABELS.items()}
    selected_model_label = st.selectbox(
        "Primary model",
        options=list(model_label_to_name.keys()),
        index=list(model_label_to_name.keys()).index(mode_settings["primary_model"]),
        key="primary_model_v42",
        help="This model is used for the main prediction and walk-forward backtest.",
    )
    selected_model_name = model_label_to_name[selected_model_label]

    comparison_set = st.selectbox(
        "Model comparison set",
        options=["Core fast", "Advanced all"],
        index=["Core fast", "Advanced all"].index(mode_settings["comparison_set"]),
        key="comparison_set_v42",
        help="Core fast compares the four practical models. Advanced all includes heavier models like CatBoost and ensembles.",
    )
    comparison_model_names = CORE_MODEL_NAMES if comparison_set == "Core fast" else ADVANCED_MODEL_NAMES

    if selected_model_name in ENSEMBLE_MODEL_NAMES:
        st.warning(
            "Ensemble models are useful for research, but they are slower. "
            "Use XGBoost or Random Forest while iterating quickly."
        )

    if analysis_mode == "Full analysis mode":
        st.warning(
            "Full analysis mode is intentionally slower because it can run advanced model comparison and "
            "walk-forward loops. Use Fast mode for quick UI checks."
        )

    st.divider()
    st.subheader("Walk-forward backtest")
    run_primary_wf = st.checkbox(
        "Run primary walk-forward backtest",
        value=mode_settings["run_primary_wf"],
        key="run_primary_wf_v42",
        help="Leave this off while testing. Turn it on when you want realistic repeated train/test evaluation.",
    )
    defaults = WALK_FORWARD_DEFAULTS.get(interval, WALK_FORWARD_DEFAULTS["1d"])

    probability_threshold = st.slider(
        "Trading probability threshold",
        min_value=0.50,
        max_value=0.75,
        value=0.55,
        step=0.01,
        help="Long-only buys when P(up) is at least this value. Long/short shorts when P(up) is below 1-threshold.",
    )
    transaction_cost_bps = st.number_input(
        "Transaction cost, bps",
        min_value=0,
        max_value=100,
        value=10,
        step=1,
        help="10 bps = 0.10% cost whenever the strategy changes position.",
    )
    run_wf_model_comparison = st.checkbox(
        "Run walk-forward comparison for all models",
        value=mode_settings["run_wf_model_comparison"],
        key="run_wf_model_comparison_v42",
        help="More realistic but slower. Leave off while iterating quickly.",
    )

    with st.expander("Advanced backtest settings"):
        initial_train_size = st.number_input(
            "Initial train rows",
            min_value=60,
            max_value=3000,
            value=defaults["initial_train_size"],
            step=10,
        )
        wf_test_size = st.number_input(
            "Test rows per fold",
            min_value=1,
            max_value=252,
            value=defaults["test_size"],
            step=1,
        )
        wf_step_size = st.number_input(
            "Step rows",
            min_value=1,
            max_value=252,
            value=defaults["step_size"],
            step=1,
        )
        max_folds = st.number_input(
            "Max recent folds",
            min_value=1,
            max_value=100,
            value=mode_settings["max_folds"],
            step=1,
            key="max_recent_folds_v42",
            help="Keeps the app responsive by using the most recent folds if many are available.",
        )

    run_button = st.button("Run prediction", type="primary")

    st.divider()
    st.caption("Educational/research use only — not financial advice.")
    st.write("Default 10-stock universe:")
    st.code(", ".join(DEFAULT_WATCHLIST))


# -----------------------------------------------------------------------------
# Top-level layout
# -----------------------------------------------------------------------------
results_root_tab, run_details_root_tab = st.tabs(["Results", "Run Details"])

with results_root_tab:
    summary_placeholder = st.empty()
    tab_prediction, tab_chart, tab_risk, tab_walk_forward, tab_comparison, tab_model, tab_data, tab_roadmap = st.tabs(
        [
            "Prediction",
            "Chart",
            "Risk Simulation",
            "Walk-forward Backtest",
            "Model Comparison",
            "Model Details",
            "Data Manager",
            "Production Roadmap",
        ]
    )

    with tab_prediction:
        prediction_placeholder = st.empty()
    with tab_chart:
        chart_placeholder = st.empty()
    with tab_risk:
        risk_placeholder = st.empty()
    with tab_walk_forward:
        walk_forward_placeholder = st.empty()
    with tab_comparison:
        comparison_placeholder = st.empty()
    with tab_model:
        model_details_placeholder = st.empty()
    with tab_data:
        data_manager_placeholder = st.empty()
    with tab_roadmap:
        roadmap_placeholder = st.empty()

with run_details_root_tab:
    st.subheader("Run Details")
    st.caption("Use this tab while the pipeline is running. It shows current stage, completed stages, and model progress.")
    progress_placeholder = st.empty()
    stage_placeholder = st.empty()
    insight_placeholder = st.empty()
    log_placeholder = st.empty()


RUN_STAGES = [
    "Price data",
    "Technical features",
    "Primary model",
    "Latest prediction",
    "Risk simulation",
    "Model comparison",
    "Primary walk-forward",
    "Walk-forward comparison",
    "Dashboard tabs",
]

run_events: list[dict] = []
run_insights: list[dict] = []
stage_status = {stage: "waiting" for stage in RUN_STAGES}
stage_detail = {stage: "" for stage in RUN_STAGES}
stage_updated = {stage: "" for stage in RUN_STAGES}


def render_waiting_state() -> None:
    """Render the clean initial page before a run starts."""
    with summary_placeholder.container():
        st.info("Enter a ticker, choose settings, and click **Run prediction**.")
        st.write("Results will populate here as each section becomes available.")

    with prediction_placeholder.container():
        st.info("Prediction has not started yet.")
    with chart_placeholder.container():
        st.info("Chart will load after price data and indicators are ready.")
    with risk_placeholder.container():
        st.info("Risk simulation will load after the latest prediction is ready.")
    with walk_forward_placeholder.container():
        st.info("Walk-forward results will appear here if enabled in the sidebar.")
    with comparison_placeholder.container():
        st.info("Model comparison will appear after the selected model set finishes training.")
    with model_details_placeholder.container():
        st.info("Model details will appear after the primary model finishes training.")
    with data_manager_placeholder.container():
        st.info("Data tables will appear after price data is downloaded.")
    render_roadmap_section()

    render_run_details(progress=0, progress_text="Idle — waiting for a run")


def _status_label(status: str) -> str:
    status_icons = {
        "waiting": "⚪ waiting",
        "running": "🟡 running",
        "complete": "🟢 complete",
        "skipped": "🔵 skipped",
        "failed": "🔴 failed",
    }
    return status_icons.get(status, status)


def render_run_details(progress: int, progress_text: str) -> None:
    """Render the run-details tab as structured tables instead of noisy text above results."""
    progress = max(0, min(100, int(progress)))
    progress_placeholder.progress(progress, text=progress_text)

    stage_df = pd.DataFrame(
        [
            {
                "section": stage_name,
                "status": _status_label(stage_status[stage_name]),
                "detail": stage_detail[stage_name],
                "last_update": stage_updated[stage_name],
            }
            for stage_name in RUN_STAGES
        ]
    )
    stage_placeholder.dataframe(stage_df, width="stretch", hide_index=True)

    if run_insights:
        insight_placeholder.dataframe(pd.DataFrame(run_insights[-12:]), width="stretch", hide_index=True)
    else:
        insight_placeholder.info("Insights will appear here after each stage finishes.")

    if run_events:
        log_placeholder.dataframe(pd.DataFrame(run_events[-20:]), width="stretch", hide_index=True)
    else:
        log_placeholder.info("No run events yet.")


def update_run_monitor(stage: str, status: str, detail: str = "", progress: int = 0, insight: str | None = None) -> None:
    """Update only the Run Details tab, not the main Results tab."""
    now = datetime.now().strftime("%H:%M:%S")
    progress = max(0, min(100, int(progress)))

    stage_status[stage] = status
    stage_detail[stage] = detail
    stage_updated[stage] = now

    if insight:
        run_insights.append({"time": now, "section": stage, "insight": insight})

    run_events.append(
        {
            "time": now,
            "section": stage,
            "status": status,
            "detail": detail,
        }
    )

    render_run_details(progress=progress, progress_text=f"{stage}: {detail or status}")


def render_summary_metrics(ticker: str, latest_close: float, latest_date, selected_model_label: str, prediction: dict, results: dict, wf_results, risk_results=None, analysis_mode: str = "Fast mode") -> None:
    with summary_placeholder.container():
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ticker", ticker)
        col2.metric("Latest close", f"${latest_close:,.2f}")
        col3.metric("Latest data date", str(latest_date))
        col4.metric("Run mode", analysis_mode)

        risk_outlook = "Risk skipped"
        if risk_results is not None:
            risk_outlook = risk_label(risk_results["summary"])

        col5, col6, col7, col8 = st.columns(4)
        col5.metric("Signal", prediction["signal"])
        col6.metric("Up probability", f"{prediction['up_probability']:.1%}")
        col7.metric("Risk-adjusted outlook", risk_outlook)
        col8.metric(
            "Walk-forward accuracy",
            "Skipped" if wf_results is None else f"{wf_results['classification_metrics']['accuracy']:.1%}",
        )


def render_prediction_section(latest_row, prediction: dict, results: dict, ticker: str, selected_model_label: str) -> None:
    with prediction_placeholder.container():
        left, right = st.columns([1, 1])

        with left:
            st.subheader("Next-period prediction")
            st.write(f"Primary model: **{selected_model_label}**")
            st.plotly_chart(make_probability_gauge(prediction["up_probability"]), width="stretch", key=f"prediction_gauge_{ticker}_{selected_model_label}")

        with right:
            st.subheader("Latest technical snapshot")
            st.write(
                {
                    "Close": round(float(latest_row["Close"]), 2),
                    "Latest return": f"{float(latest_row['return_1d']):.2%}",
                    "RSI 14": round(float(latest_row["rsi_14"]), 2),
                    "MACD diff": round(float(latest_row["macd_diff"]), 4),
                    "20-period volatility": f"{float(latest_row['volatility_20']):.2%}",
                    "ATR %": f"{float(latest_row['atr_pct']):.2%}",
                    "Bollinger position": round(float(latest_row["bb_position"]), 3),
                }
            )

        st.subheader("Simple test split preview")
        st.plotly_chart(make_backtest_preview(results["test"], results["test_probabilities"], ticker), width="stretch", key=f"simple_backtest_preview_{ticker}_{selected_model_label}")


def render_chart_section(feature_df: pd.DataFrame, ticker: str) -> None:
    with chart_placeholder.container():
        st.plotly_chart(make_price_chart(feature_df, ticker), width="stretch", key=f"price_chart_{ticker}")


def render_risk_simulation_section(risk_results: dict | None, ticker: str, interval: str, selected_drift_label: str) -> None:
    with risk_placeholder.container():
        st.subheader("Monte Carlo risk simulation")
        st.write(
            "This simulation estimates a range of possible future prices from recent volatility. "
            "It is a risk lens, not a guarantee or trading instruction."
        )

        if risk_results is None:
            st.info("Risk simulation was skipped. Turn on **Run Monte Carlo risk simulation** in the sidebar.")
            return

        summary = risk_results["summary"]
        label = risk_label(summary)

        st.info(
            f"Meroq estimates a **{label.lower()}**: median simulated return is "
            f"{summary['median_return']:.1%}, with a {summary['probability_loss_gt_5pct']:.1%} chance "
            f"of losing more than 5% over the next {summary['horizon']} periods."
        )

        a, b, c, d = st.columns(4)
        a.metric("Risk label", label)
        b.metric("Median final price", f"${summary['median_final_price']:,.2f}", f"{summary['median_return']:.1%}")
        c.metric("10th percentile", f"${summary['p10_final_price']:,.2f}", f"{summary['p10_return']:.1%}")
        d.metric("90th percentile", f"${summary['p90_final_price']:,.2f}", f"{summary['p90_return']:.1%}")

        e, f, g, h = st.columns(4)
        e.metric("Positive return probability", f"{summary['probability_positive_return']:.1%}")
        f.metric("Loss > 5% probability", f"{summary['probability_loss_gt_5pct']:.1%}")
        g.metric("Gain > 5% probability", f"{summary['probability_gain_gt_5pct']:.1%}")
        h.metric("Expected max drawdown", f"{summary['expected_max_drawdown']:.1%}")

        st.plotly_chart(make_monte_carlo_percentile_chart(risk_results["percentiles"], ticker), width="stretch", key=f"mc_percentiles_{ticker}_{summary['horizon']}_{summary['n_paths']}")
        st.plotly_chart(make_final_return_distribution_chart(risk_results["final_distribution"], ticker), width="stretch", key=f"mc_return_distribution_{ticker}_{summary['horizon']}_{summary['n_paths']}")

        with st.expander("Show sample simulated paths"):
            st.plotly_chart(make_monte_carlo_sample_paths_chart(risk_results["paths"], ticker), width="stretch", key=f"mc_sample_paths_{ticker}_{summary['horizon']}_{summary['n_paths']}")

        with st.expander("Simulation assumptions and summary"):
            assumption_df = pd.DataFrame([
                {
                    "interval": interval,
                    "horizon_periods": summary["horizon"],
                    "simulation_paths": summary["n_paths"],
                    "drift_assumption": selected_drift_label,
                    "period_drift": summary["period_drift"],
                    "period_volatility": summary["period_volatility"],
                    "volatility_window": summary["volatility_window"],
                    "current_price": summary["current_price"],
                    "expected_final_price": summary["expected_final_price"],
                    "expected_return": summary["expected_return"],
                }
            ])
            st.dataframe(assumption_df, width="stretch")


def render_walk_forward_section(wf_results, selected_model_label: str, interval: str, ticker: str) -> None:
    with walk_forward_placeholder.container():
        st.subheader("Walk-forward validation")
        st.write(
            "Walk-forward validation repeatedly trains on past data and predicts the next unseen future window."
        )

        if wf_results is None:
            st.info(
                "Walk-forward backtesting was skipped to keep the app fast. "
                "Turn on **Run primary walk-forward backtest** in the sidebar when you want realistic evaluation."
            )
            st.write("Suggested fast settings:")
            st.code(
                "Primary model: XGBoost or Random Forest\n"
                "Max recent folds: 6 to 10\n"
                "Model comparison set: Core fast\n"
                "Avoid Stacking Ensemble for quick testing"
            )
            return

        st.write(f"Primary model: **{selected_model_label}**")

        wf_class = wf_results["classification_metrics"]
        long_metrics = wf_results["long_metrics"]
        long_short_metrics = wf_results["long_short_metrics"]
        wf_settings = wf_results["settings"]

        a, b, c, d = st.columns(4)
        a.metric("Folds", wf_settings["folds"])
        b.metric("WF accuracy", f"{wf_class['accuracy']:.1%}")
        c.metric("WF F1", f"{wf_class['f1']:.1%}")
        d.metric("WF ROC-AUC", "N/A" if pd.isna(wf_class["roc_auc"]) else f"{wf_class['roc_auc']:.3f}")

        e, f, g, h = st.columns(4)
        e.metric("Long-only return", f"{long_metrics['strategy_total_return']:.1%}")
        f.metric("Buy & hold return", f"{long_metrics['buy_hold_return']:.1%}")
        g.metric("Long-only Sharpe", "N/A" if pd.isna(long_metrics["sharpe_ratio"]) else f"{long_metrics['sharpe_ratio']:.2f}")
        h.metric("Long-only max DD", f"{long_metrics['max_drawdown']:.1%}")

        i, j, k, l = st.columns(4)
        i.metric("Long/short return", f"{long_short_metrics['strategy_total_return']:.1%}")
        j.metric("Long/short Sharpe", "N/A" if pd.isna(long_short_metrics["sharpe_ratio"]) else f"{long_short_metrics['sharpe_ratio']:.2f}")
        k.metric("Long/short max DD", f"{long_short_metrics['max_drawdown']:.1%}")
        l.metric("Long-only trades", long_metrics["trades"])

        st.plotly_chart(make_equity_curve_chart(wf_results["predictions"], ticker), width="stretch", key=f"wf_equity_curve_{ticker}_{selected_model_label}")
        st.plotly_chart(make_probability_backtest_chart(wf_results["predictions"], ticker), width="stretch", key=f"wf_probability_{ticker}_{selected_model_label}")
        st.plotly_chart(make_drawdown_chart(wf_results["predictions"]), width="stretch", key=f"wf_drawdown_{ticker}_{selected_model_label}")

        with st.expander("Walk-forward fold details"):
            st.dataframe(wf_results["folds"], width="stretch")

        with st.expander("Walk-forward prediction rows"):
            show_cols = [
                "Date",
                "model",
                "Close",
                "next_return",
                "target_up_tomorrow",
                "proba_up",
                "pred_up",
                "long_position",
                "long_strategy_return",
                "long_short_position",
                "long_short_strategy_return",
            ]
            st.dataframe(wf_results["predictions"][show_cols].tail(250), width="stretch")


def render_comparison_section(simple_comparison: pd.DataFrame, wf_comparison: pd.DataFrame, run_wf_model_comparison: bool, render_key: str = "default") -> None:
    with comparison_placeholder.container():
        st.subheader("Model comparison")
        st.write(
            "This compares baseline, linear, tree ensemble, boosting, and ensemble models. "
            "The most complex model is not automatically the best; the goal is out-of-sample behavior."
        )

        st.markdown("### Model availability")
        st.dataframe(model_dependency_status(), width="stretch")

        st.markdown("### Simple chronological split")
        st.dataframe(simple_comparison, width="stretch")
        st.plotly_chart(make_model_metric_bar_chart(simple_comparison, "roc_auc", "Simple Split ROC-AUC by Model"), width="stretch", key=f"simple_model_comparison_roc_auc_{render_key}")
        st.plotly_chart(make_model_metric_bar_chart(simple_comparison, "f1", "Simple Split F1 by Model"), width="stretch", key=f"simple_model_comparison_f1_{render_key}")

        best_ok = simple_comparison[simple_comparison["status"] == "ok"]
        if not best_ok.empty:
            best_row = best_ok.iloc[0]
            roc_auc = best_row.get("roc_auc")
            roc_text = "N/A" if pd.isna(roc_auc) else f"{roc_auc:.3f}"
            st.success(
                f"Best simple-split model by ROC-AUC/F1/accuracy: **{best_row['model']}** "
                f"with ROC-AUC {roc_text}."
            )

        st.markdown("### Walk-forward model comparison")
        if run_wf_model_comparison:
            st.dataframe(wf_comparison, width="stretch")
            st.plotly_chart(make_model_metric_bar_chart(wf_comparison, "roc_auc", "Walk-Forward ROC-AUC by Model"), width="stretch", key=f"wf_model_comparison_roc_auc_{render_key}")
            st.plotly_chart(make_walk_forward_model_return_chart(wf_comparison), width="stretch", key=f"wf_model_comparison_returns_{render_key}")
        else:
            st.info(
                "Turn on **Run walk-forward comparison for all models** in the sidebar to compare the selected model set "
                "with the more realistic walk-forward method. Use **Core fast** first; **Advanced all** can be slow."
            )


def render_model_details_section(results: dict, selected_model_label: str) -> None:
    with model_details_placeholder.container():
        st.subheader("Primary model details")
        st.write(f"Selected model: **{selected_model_label}**")

        st.subheader("Simple chronological train/test metrics")
        st.dataframe(pd.DataFrame([results["metrics"]]), width="stretch")

        st.subheader("Feature importance / coefficient magnitude")
        st.plotly_chart(make_feature_importance_chart(results["feature_importance"]), width="stretch", key=f"feature_importance_{selected_model_label}")

        st.warning(
            "Low accuracy is normal for market direction prediction. The goal is not just accuracy; it is robust "
            "out-of-sample behavior, realistic costs, and comparison against simple baselines."
        )


def render_data_manager_section(raw_df: pd.DataFrame | None = None, model_frame: pd.DataFrame | None = None) -> None:
    with data_manager_placeholder.container():
        st.subheader("Saved local database")
        saved_tables = list_saved_price_tables()
        if saved_tables:
            st.write("Saved tables in `data/market_data.sqlite`:")
            st.code("\n".join(saved_tables))
        else:
            st.write("No local SQLite tables found yet. Running the app or bootstrap script will create them.")

        if raw_df is not None:
            st.subheader("Raw price data")
            st.dataframe(raw_df.tail(100), width="stretch")

        if model_frame is not None:
            st.subheader("Model training data")
            st.dataframe(model_frame.tail(100), width="stretch")


def render_roadmap_section() -> None:
    with roadmap_placeholder.container():
        st.subheader("Production-minded upgrade path")
        st.markdown(
            """
            **Current stage: Stage 4.2 — Stability, safe defaults, documentation, and Git readiness.**

            What this stage improves:

            1. Adds an **Analysis mode** selector so fast, research, and full runs are intentional.
            2. Uses safe defaults: XGBoost, Core fast comparison, Monte Carlo on, slow walk-forward loops off.
            3. Keeps product results in **Results** and operational status in **Run Details**.
            4. Adds clearer risk interpretation and risk-adjusted outlook metrics.
            5. Adds project documentation so the repo can be initialized cleanly before Stage 5.

            Next upgrades:

            1. Add a news ingestion layer and FinBERT sentiment features.
            2. Add API-key configuration through `.env` and Streamlit secrets.
            3. Save sentiment features into the local database.
            4. Compare model performance with and without sentiment features.
            5. Move from SQLite to PostgreSQL once data grows.
            """
        )


def simple_comparison_progress(payload: dict) -> None:
    """Progress callback for simple model comparison."""
    index = int(payload.get("index", 0) or 0)
    total = max(1, int(payload.get("total", 1) or 1))
    model_label = payload.get("model", payload.get("model_name", "model"))
    pct = 50 + int(15 * index / total)

    if payload.get("status") == "running":
        update_run_monitor(
            "Model comparison",
            "running",
            f"Training {model_label} ({index}/{total})",
            pct,
        )
    elif payload.get("status") == "complete":
        metrics = payload.get("metrics", {})
        auc = metrics.get("roc_auc")
        auc_text = "N/A" if pd.isna(auc) else f"{auc:.3f}"
        update_run_monitor(
            "Model comparison",
            "running" if index < total else "complete",
            f"Finished {model_label} ({index}/{total})",
            pct,
            f"{model_label} simple split: accuracy {metrics.get('accuracy', float('nan')):.1%}, ROC-AUC {auc_text}.",
        )
    elif payload.get("status") == "failed":
        update_run_monitor(
            "Model comparison",
            "running" if index < total else "complete",
            f"{model_label} failed: {payload.get('error', 'unknown error')}",
            pct,
        )


def primary_walk_forward_progress(payload: dict) -> None:
    """Progress callback for the selected model's walk-forward backtest."""
    fold = int(payload.get("fold", 0) or 0)
    total = max(1, int(payload.get("total_folds", 1) or 1))
    model_label = payload.get("model", selected_model_label)
    pct = 66 + int(17 * fold / total)

    if payload.get("status") == "running":
        update_run_monitor(
            "Primary walk-forward",
            "running",
            f"{model_label}: fold {fold}/{total}, train rows {payload.get('train_rows')}",
            pct,
        )
    elif payload.get("status") == "complete":
        update_run_monitor(
            "Primary walk-forward",
            "running" if fold < total else "complete",
            f"{model_label}: completed fold {fold}/{total}",
            pct,
        )


def model_walk_forward_progress(payload: dict) -> None:
    """Progress callback for walk-forward comparison across models."""
    model_index = int(payload.get("model_index", 0) or 0)
    model_total = max(1, int(payload.get("model_total", 1) or 1))
    fold = int(payload.get("fold", 0) or 0)
    total_folds = max(1, int(payload.get("total_folds", 1) or 1))
    model_label = payload.get("model", payload.get("model_name", "model"))
    within_model = fold / total_folds if fold else 0
    pct = 84 + int(11 * ((model_index - 1 + within_model) / model_total))

    if payload.get("status") == "running":
        if fold:
            detail = f"{model_label}: model {model_index}/{model_total}, fold {fold}/{total_folds}"
        else:
            detail = f"Starting {model_label} ({model_index}/{model_total})"
        update_run_monitor("Walk-forward comparison", "running", detail, pct)
    elif payload.get("status") == "complete":
        update_run_monitor(
            "Walk-forward comparison",
            "running" if model_index < model_total else "complete",
            f"Finished {model_label} ({model_index}/{model_total})",
            pct,
        )
    elif payload.get("status") == "failed":
        update_run_monitor(
            "Walk-forward comparison",
            "running" if model_index < model_total else "complete",
            f"{model_label} failed: {payload.get('error', 'unknown error')}",
            pct,
        )


if not run_button:
    render_waiting_state()
    st.stop()

# Initial clean states for this run.
with summary_placeholder.container():
    st.info("Pipeline is running. Open **Run Details** to watch progress. Results tabs will populate as soon as their data is ready.")
with prediction_placeholder.container():
    st.info("Waiting for latest prediction...")
with chart_placeholder.container():
    st.info("Waiting for price chart...")
with risk_placeholder.container():
    st.info("Waiting for risk simulation...")
with walk_forward_placeholder.container():
    st.info("Waiting for walk-forward settings...")
with comparison_placeholder.container():
    st.info("Waiting for model comparison...")
with model_details_placeholder.container():
    st.info("Waiting for primary model details...")
with data_manager_placeholder.container():
    st.info("Waiting for data...")
render_roadmap_section()

try:
    update_run_monitor("Price data", "running", f"Downloading {ticker} {period} {interval} in {analysis_mode}", 5)
    raw_df = fetch_price_data(ticker=ticker, period=period, interval=interval)
    raw_start = pd.to_datetime(raw_df["Date"].iloc[0]).date()
    raw_end = pd.to_datetime(raw_df["Date"].iloc[-1]).date()
    update_run_monitor(
        "Price data",
        "complete",
        f"Loaded {len(raw_df):,} rows from {raw_start} to {raw_end}",
        15,
        f"Price data loaded: {ticker} has {len(raw_df):,} rows from {raw_start} to {raw_end}.",
    )
    render_data_manager_section(raw_df=raw_df)

    update_run_monitor("Technical features", "running", "Calculating indicators", 20)
    feature_df = add_technical_features(raw_df).dropna().reset_index(drop=True)
    model_frame = build_model_frame(raw_df)
    min_rows = 120 if interval == "1wk" else 180
    update_run_monitor(
        "Technical features",
        "complete",
        f"Built {len(model_frame):,} usable ML rows",
        28,
        f"Feature engineering complete: {len(model_frame):,} usable rows after indicators and target creation.",
    )
    render_chart_section(feature_df, ticker)
    render_data_manager_section(raw_df=raw_df, model_frame=model_frame)

    update_run_monitor("Primary model", "running", f"Training {selected_model_label}", 34)
    results = train_classifier(
        model_frame=model_frame,
        model_name=selected_model_name,
        min_rows=min_rows,
        n_estimators=300,
    )
    primary_auc = results["metrics"].get("roc_auc")
    primary_auc_text = "N/A" if pd.isna(primary_auc) else f"{primary_auc:.3f}"
    update_run_monitor(
        "Primary model",
        "complete",
        f"{selected_model_label} trained",
        42,
        f"Primary model trained: {selected_model_label} simple-split accuracy {results['metrics']['accuracy']:.1%}, ROC-AUC {primary_auc_text}.",
    )
    render_model_details_section(results, selected_model_label)

    update_run_monitor("Latest prediction", "running", "Scoring latest row", 44)
    latest_row = feature_df.iloc[-1]
    prediction = predict_latest(results["model"], latest_row)
    update_run_monitor(
        "Latest prediction",
        "complete",
        f"Signal {prediction['signal']} at {prediction['up_probability']:.1%} up probability",
        46,
        f"Latest prediction: {prediction['signal']} with {prediction['up_probability']:.1%} probability of an upward next-period move.",
    )
    latest_close = float(raw_df["Close"].iloc[-1])
    latest_date = pd.to_datetime(raw_df["Date"].iloc[-1]).date()
    render_summary_metrics(ticker, latest_close, latest_date, selected_model_label, prediction, results, None, risk_results=None, analysis_mode=analysis_mode)
    render_prediction_section(latest_row, prediction, results, ticker, selected_model_label)

    risk_results = None
    if run_risk_simulation:
        update_run_monitor(
            "Risk simulation",
            "running",
            f"Simulating {simulation_paths:,} paths across {simulation_horizon} periods",
            47,
        )
        risk_results = simulate_price_paths(
            price_df=raw_df,
            horizon=int(simulation_horizon),
            n_paths=int(simulation_paths),
            volatility_window=int(volatility_window),
            drift_mode=drift_mode,
            model_up_probability=float(prediction["up_probability"]),
            random_seed=42,
        )
        risk_summary = risk_results["summary"]
        update_run_monitor(
            "Risk simulation",
            "complete",
            f"Median {risk_summary['median_return']:.1%}, downside >5% {risk_summary['probability_loss_gt_5pct']:.1%}",
            49,
            f"Risk simulation complete: median return {risk_summary['median_return']:.1%}; probability of loss greater than 5% is {risk_summary['probability_loss_gt_5pct']:.1%}.",
        )
    else:
        update_run_monitor(
            "Risk simulation",
            "skipped",
            "Skipped in sidebar",
            49,
        )

    render_risk_simulation_section(risk_results, ticker, interval, selected_drift_label)

    update_run_monitor(
        "Model comparison",
        "running",
        f"Comparing {len(comparison_model_names)} models",
        50,
    )
    simple_comparison, simple_results_by_model = compare_models_simple_split(
        model_frame=model_frame,
        model_names=comparison_model_names,
        min_rows=min_rows,
        progress_callback=simple_comparison_progress,
    )
    best_ok = simple_comparison[simple_comparison["status"] == "ok"]
    if not best_ok.empty:
        best_row_for_monitor = best_ok.iloc[0]
        update_run_monitor(
            "Model comparison",
            "complete",
            f"Best simple split: {best_row_for_monitor['model']}",
            65,
            f"Best simple-split model so far: {best_row_for_monitor['model']} by ROC-AUC/F1/accuracy ranking.",
        )
    else:
        update_run_monitor("Model comparison", "complete", "No successful model comparisons", 65)

    wf_results = None
    wf_comparison = pd.DataFrame()
    wf_results_by_model = {}
    render_comparison_section(simple_comparison, wf_comparison, run_wf_model_comparison=False, render_key="simple_preview")

    if run_primary_wf:
        update_run_monitor(
            "Primary walk-forward",
            "running",
            f"Running {selected_model_label} walk-forward backtest",
            66,
        )
        wf_results = walk_forward_backtest(
            model_frame=model_frame,
            initial_train_size=int(initial_train_size),
            test_size=int(wf_test_size),
            step_size=int(wf_step_size),
            probability_threshold=float(probability_threshold),
            transaction_cost_bps=float(transaction_cost_bps),
            periods_per_year=WALK_FORWARD_DEFAULTS.get(interval, WALK_FORWARD_DEFAULTS["1d"])["periods_per_year"],
            max_folds=int(max_folds),
            n_estimators=80 if selected_model_name in ENSEMBLE_MODEL_NAMES else 120,
            model_name=selected_model_name,
            progress_callback=primary_walk_forward_progress,
        )
        update_run_monitor(
            "Primary walk-forward",
            "complete",
            f"{wf_results['settings']['folds']} folds complete",
            83,
            f"Walk-forward complete: {wf_results['settings']['folds']} folds, accuracy {wf_results['classification_metrics']['accuracy']:.1%}.",
        )
    else:
        update_run_monitor(
            "Primary walk-forward",
            "skipped",
            "Skipped for speed; enable in sidebar for realistic evaluation",
            83,
        )

    render_summary_metrics(ticker, latest_close, latest_date, selected_model_label, prediction, results, wf_results, risk_results=risk_results, analysis_mode=analysis_mode)
    render_walk_forward_section(wf_results, selected_model_label, interval, ticker)

    if run_wf_model_comparison:
        update_run_monitor(
            "Walk-forward comparison",
            "running",
            f"Comparing {len(comparison_model_names)} models with walk-forward validation",
            84,
        )
        wf_comparison, wf_results_by_model = compare_models_walk_forward(
            model_frame=model_frame,
            model_names=comparison_model_names,
            initial_train_size=int(initial_train_size),
            test_size=int(wf_test_size),
            step_size=int(wf_step_size),
            probability_threshold=float(probability_threshold),
            transaction_cost_bps=float(transaction_cost_bps),
            periods_per_year=WALK_FORWARD_DEFAULTS.get(interval, WALK_FORWARD_DEFAULTS["1d"])["periods_per_year"],
            max_folds=min(int(max_folds), 15),
            n_estimators=120,
            progress_callback=model_walk_forward_progress,
        )
        update_run_monitor(
            "Walk-forward comparison",
            "complete",
            f"Compared {len(wf_comparison)} models",
            95,
        )
    else:
        update_run_monitor(
            "Walk-forward comparison",
            "skipped",
            "Skipped for speed; enable in sidebar for research mode",
            95,
        )

    render_comparison_section(simple_comparison, wf_comparison, run_wf_model_comparison=run_wf_model_comparison, render_key="final")

    update_run_monitor(
        "Dashboard tabs",
        "complete",
        "All result sections are ready",
        100,
        "Dashboard is ready: Prediction, Chart, Risk Simulation, Backtest, Model Comparison, Model Details, Data Manager, and Roadmap sections are loaded.",
    )

except Exception as exc:
    update_run_monitor("Dashboard tabs", "failed", str(exc), 100)
    with summary_placeholder.container():
        st.error(f"Something went wrong: {exc}")
    st.stop()
