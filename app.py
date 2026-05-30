from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
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
    make_sentiment_label_chart,
    make_sentiment_score_chart,
    make_sentiment_timeline_chart,
    make_probability_backtest_chart,
    make_probability_gauge,
    make_walk_forward_model_return_chart,
)
from src.config import DEFAULT_WATCHLIST, SUGGESTED_INTERVALS, SUGGESTED_PERIODS, WALK_FORWARD_DEFAULTS
from src.data_loader import fetch_price_data, list_saved_price_tables
from src.storage import database_file_summary, inspect_market_database, inspect_news_cache, inspect_sentiment_features, load_daily_sentiment_features, save_daily_sentiment_features
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
from src.news_sentiment import (
    NEWS_SOURCE_OPTIONS,
    SENTIMENT_ENGINE_OPTIONS,
    analyze_news_sentiment,
    fetch_news_for_ticker,
    sentiment_context_sentence,
    sentiment_engine_availability,
    summarize_sentiment,
)
from src.sentiment_features import aggregate_daily_sentiment, build_latest_sentiment_feature_row, merge_daily_sentiment_frames
from src.signal_fusion import build_signal_components_frame, fuse_prediction_with_sentiment
from src.sentiment_modeling import (
    analyze_sentiment_modeling_readiness,
    compare_base_vs_sentiment_simple_split,
)
from src.watchlist import scan_watchlist, summarize_watchlist_scan
from src.reporting import build_insight_report


st.set_page_config(page_title="Meroq", page_icon="📈", layout="wide")

st.title("📈 Meroq")
st.caption("Predictive market intelligence with model comparison, news sentiment, risk simulation, watchlist scanning, and exportable reports.")

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    [data-testid="stSidebar"] .stExpander {border: 1px solid rgba(255,255,255,0.08); border-radius: 0.6rem;}
    [data-testid="stMetricValue"] {font-size: 1.55rem;}
    div[data-testid="stDataFrame"] {font-size: 0.88rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

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
        key="analysis_mode_v82",
        help=(
            "Fast mode keeps the app responsive. Research mode adds the primary walk-forward backtest. "
            "Full analysis mode enables heavier comparisons. Custom lets you choose manually."
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
            "Fast mode": "Recommended default: fast prediction, news sentiment, and Monte Carlo risk.",
            "Research mode": "Adds a limited walk-forward backtest for the selected model.",
            "Full analysis mode": "Heavier research run with advanced comparison. Expect slower execution.",
            "Custom": "Manual control over model, risk, news, and backtesting settings.",
        }[analysis_mode]
    )

    run_button = st.button("Run prediction", type="primary", width="stretch")

    with st.expander("Watchlist scan", expanded=False):
        run_watchlist_scan = st.checkbox(
            "Run watchlist intelligence scan",
            value=False,
            key="run_watchlist_scan_v90",
            help="Scans multiple tickers with a fast model, recent sentiment, and lightweight risk metrics.",
        )
        watchlist_text = st.text_area(
            "Watchlist tickers",
            value=", ".join(DEFAULT_WATCHLIST),
            key="watchlist_text_v90",
            height=80,
            help="Comma-separated symbols. Keep this under 20 tickers for responsive local runs.",
        )
        watchlist_max_tickers = st.selectbox(
            "Max tickers to scan",
            options=[5, 10, 15, 20],
            index=1,
            key="watchlist_max_tickers_v90",
        )
        watchlist_include_sentiment = st.checkbox(
            "Include recent-news sentiment",
            value=True,
            key="watchlist_include_sentiment_v90",
        )
        watchlist_include_risk = st.checkbox(
            "Include lightweight risk simulation",
            value=True,
            key="watchlist_include_risk_v90",
        )
        st.caption("Uses XGBoost with lighter settings by default so the scan stays practical.")

    with st.expander("Risk simulation", expanded=False):
        run_risk_simulation = st.checkbox(
            "Run Monte Carlo risk simulation",
            value=True,
            key="run_risk_simulation_v82",
            help="Fast simulation that estimates future price ranges and downside risk from recent volatility.",
        )
        simulation_horizon = st.selectbox(
            "Simulation horizon",
            options=[10, 21, 30, 60, 90],
            index=2,
            key="simulation_horizon_v82",
        )
        simulation_paths = st.selectbox(
            "Simulation paths",
            options=[500, 1000, 2500, 5000],
            index=1,
            key="simulation_paths_v82",
        )
        volatility_window = st.selectbox(
            "Volatility window",
            options=[20, 60, 126, 252],
            index=1,
            key="volatility_window_v82",
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
            key="drift_assumption_v82",
        )
        drift_mode = drift_label_to_mode[selected_drift_label]

    with st.expander("News sentiment", expanded=False):
        run_sentiment_analysis = st.checkbox(
            "Run news sentiment analysis",
            value=True,
            key="run_sentiment_analysis_v82",
        )
        news_source_key_to_label = {key: label for key, label in NEWS_SOURCE_OPTIONS.items()}
        news_source_label_to_key = {label: key for key, label in NEWS_SOURCE_OPTIONS.items()}
        selected_news_source_label = st.selectbox(
            "News source",
            options=list(news_source_label_to_key.keys()),
            index=0,
            key="news_source_v82",
        )
        selected_news_source = news_source_label_to_key[selected_news_source_label]

        sentiment_engine_label_to_key = {label: key for key, label in SENTIMENT_ENGINE_OPTIONS.items()}
        selected_sentiment_engine_label = st.selectbox(
            "Sentiment engine",
            options=list(sentiment_engine_label_to_key.keys()),
            index=list(sentiment_engine_label_to_key.keys()).index("Lightweight financial lexicon"),
            key="sentiment_engine_v82",
        )
        selected_sentiment_engine = sentiment_engine_label_to_key[selected_sentiment_engine_label]

        max_news_items = st.selectbox(
            "Max headlines",
            options=[10, 20, 30, 50],
            index=2,
            key="max_news_items_v82",
        )
        news_lookback_days = st.selectbox(
            "News lookback window",
            options=[7, 14, 30],
            index=1,
            key="news_lookback_days_v82",
        )
        cache_news_locally = st.checkbox(
            "Cache news locally",
            value=True,
            key="cache_news_locally_v82",
        )
        force_news_refresh = st.checkbox(
            "Force news refresh",
            value=False,
            key="force_news_refresh_v82",
        )
        st.caption("Optional API keys are read from local .env only. They are not stored in Git.")

    with st.expander("Signal fusion", expanded=False):
        run_sentiment_fusion = st.checkbox(
            "Use sentiment-aware signal overlay",
            value=True,
            key="run_sentiment_fusion_v82",
        )
        sentiment_max_adjustment = st.slider(
            "Max sentiment probability adjustment",
            min_value=0.00,
            max_value=0.15,
            value=0.08,
            step=0.01,
            key="sentiment_max_adjustment_v82",
        )
        run_sentiment_modeling_experiment = st.checkbox(
            "Run sentiment modeling experiment",
            value=False,
            key="run_sentiment_modeling_experiment_v82",
        )
        sentiment_model_lag_days = st.selectbox(
            "Sentiment feature lag",
            options=[1, 2, 3],
            index=0,
            key="sentiment_model_lag_days_v82",
        )

    with st.expander("Model settings", expanded=False):
        model_label_to_name = {label: name for name, label in MODEL_LABELS.items()}
        selected_model_label = st.selectbox(
            "Primary model",
            options=list(model_label_to_name.keys()),
            index=list(model_label_to_name.keys()).index(mode_settings["primary_model"]),
            key="primary_model_v82",
        )
        selected_model_name = model_label_to_name[selected_model_label]

        comparison_set = st.selectbox(
            "Model comparison set",
            options=["Core fast", "Advanced all"],
            index=["Core fast", "Advanced all"].index(mode_settings["comparison_set"]),
            key="comparison_set_v82",
        )
        comparison_model_names = CORE_MODEL_NAMES if comparison_set == "Core fast" else ADVANCED_MODEL_NAMES

        if selected_model_name in ENSEMBLE_MODEL_NAMES:
            st.warning("Ensemble models are slower. Use XGBoost while iterating.")

    with st.expander("Walk-forward backtest", expanded=False):
        run_primary_wf = st.checkbox(
            "Run primary walk-forward backtest",
            value=mode_settings["run_primary_wf"],
            key="run_primary_wf_v82",
        )
        defaults = WALK_FORWARD_DEFAULTS.get(interval, WALK_FORWARD_DEFAULTS["1d"])

        probability_threshold = st.slider(
            "Trading probability threshold",
            min_value=0.50,
            max_value=0.75,
            value=0.55,
            step=0.01,
        )
        transaction_cost_bps = st.number_input(
            "Transaction cost, bps",
            min_value=0,
            max_value=100,
            value=10,
            step=1,
        )
        run_wf_model_comparison = st.checkbox(
            "Run walk-forward comparison for all models",
            value=mode_settings["run_wf_model_comparison"],
            key="run_wf_model_comparison_v82",
        )

        st.caption("Advanced backtest settings")
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
            key="max_recent_folds_v82",
        )

    with st.expander("Universe and disclaimer", expanded=False):
        st.caption("Educational/research use only — not financial advice.")
        st.write("Default 10-stock universe:")
        st.code(", ".join(DEFAULT_WATCHLIST))


# -----------------------------------------------------------------------------
# Top-level layout
# -----------------------------------------------------------------------------
results_root_tab, run_details_root_tab = st.tabs(["Results", "Run Details"])

with results_root_tab:
    summary_placeholder = st.empty()
    tab_prediction, tab_watchlist, tab_report, tab_chart, tab_risk, tab_sentiment, tab_sentiment_modeling, tab_walk_forward, tab_comparison, tab_model, tab_data, tab_roadmap = st.tabs(
        [
            "Prediction",
            "Watchlist",
            "Report",
            "Chart",
            "Risk Simulation",
            "News Sentiment",
            "Sentiment Modeling",
            "Walk-forward Backtest",
            "Model Comparison",
            "Model Details",
            "Data Manager",
            "Production Roadmap",
        ]
    )

    with tab_prediction:
        prediction_placeholder = st.empty()
    with tab_watchlist:
        watchlist_placeholder = st.empty()
    with tab_report:
        report_placeholder = st.empty()
    with tab_chart:
        chart_placeholder = st.empty()
    with tab_risk:
        risk_placeholder = st.empty()
    with tab_sentiment:
        sentiment_placeholder = st.empty()
    with tab_sentiment_modeling:
        sentiment_modeling_placeholder = st.empty()
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
    "News sentiment",
    "Sentiment-aware signal",
    "Sentiment modeling",
    "Watchlist scan",
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
    with watchlist_placeholder.container():
        st.info("Watchlist scan will appear here if enabled in the sidebar.")
    with report_placeholder.container():
        st.info("Run a prediction to generate a downloadable Meroq insight report.")
    with chart_placeholder.container():
        st.info("Chart will load after price data and indicators are ready.")
    with risk_placeholder.container():
        st.info("Risk simulation will load after the latest prediction is ready.")
    with sentiment_placeholder.container():
        st.info("News sentiment will load after recent headlines are fetched and scored.")
    with sentiment_modeling_placeholder.container():
        st.info("Sentiment modeling readiness will load after daily sentiment features are created.")
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


def render_summary_metrics(
    ticker: str,
    latest_close: float,
    latest_date,
    selected_model_label: str,
    prediction: dict,
    results: dict,
    wf_results,
    risk_results=None,
    sentiment_summary=None,
    sentiment_fusion=None,
    analysis_mode: str = "Fast mode",
) -> None:
    with summary_placeholder.container():
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ticker", ticker)
        col2.metric("Latest close", f"${latest_close:,.2f}")
        col3.metric("Latest data date", str(latest_date))
        col4.metric("Run mode", analysis_mode)

        risk_outlook = "Risk skipped"
        if risk_results is not None:
            risk_outlook = risk_label(risk_results["summary"])

        adjusted_signal = prediction["signal"]
        adjusted_probability = prediction["up_probability"]
        adjustment_text = "N/A"
        if sentiment_fusion is not None and sentiment_fusion.get("available"):
            adjusted_signal = sentiment_fusion["signal"]
            adjusted_probability = sentiment_fusion["adjusted_up_probability"]
            adjustment_text = f"{sentiment_fusion['adjustment_pct_points']:+.2f} pp"

        col5, col6, col7, col8 = st.columns(4)
        col5.metric("Base signal", prediction["signal"])
        col6.metric("Base up probability", f"{prediction['up_probability']:.1%}")
        col7.metric("Sentiment-aware signal", adjusted_signal, adjustment_text)
        col8.metric("Adjusted up probability", f"{adjusted_probability:.1%}")

        sent_label = "Skipped"
        sent_score = "N/A"
        if sentiment_summary is not None:
            sent_label = sentiment_summary.get("overall_label", "No news")
            sent_score = f"{sentiment_summary.get('average_score', 0.0):+.2f}" if sentiment_summary.get("available") else "N/A"
        col9, col10, col11, col12 = st.columns(4)
        col9.metric("News sentiment", sent_label, sent_score)
        col10.metric("Risk-adjusted outlook", risk_outlook)
        col11.metric("Walk-forward accuracy", "Skipped" if wf_results is None else f"{wf_results['classification_metrics']['accuracy']:.1%}")
        col12.metric("Model confidence lens", "Low" if results['metrics']['accuracy'] < 0.52 else "Moderate")


def render_prediction_section(latest_row, prediction: dict, results: dict, ticker: str, selected_model_label: str, sentiment_fusion=None, render_key: str = "final") -> None:
    with prediction_placeholder.container():
        st.subheader("Prediction summary")

        adjusted_probability = prediction["up_probability"]
        adjusted_signal = prediction["signal"]
        adjustment_text = "No overlay"
        if sentiment_fusion is not None and sentiment_fusion.get("available"):
            adjusted_probability = sentiment_fusion["adjusted_up_probability"]
            adjusted_signal = sentiment_fusion["signal"]
            adjustment_text = f"{sentiment_fusion['adjustment_pct_points']:+.2f} percentage points"

        a, b, c, d = st.columns(4)
        a.metric("Base signal", prediction["signal"])
        b.metric("Base up probability", f"{prediction['up_probability']:.1%}")
        c.metric("Final signal", adjusted_signal)
        d.metric("Final up probability", f"{adjusted_probability:.1%}", adjustment_text)

        st.progress(float(adjusted_probability), text=f"Final up-probability estimate: {adjusted_probability:.1%}")

        if sentiment_fusion is not None and sentiment_fusion.get("available"):
            st.info(f"{sentiment_fusion['explanation']} {sentiment_fusion['reason']}")
            components = build_signal_components_frame(sentiment_fusion)
            if not components.empty:
                st.dataframe(components, width="stretch", hide_index=True)
        else:
            st.caption("Sentiment overlay is unavailable or disabled. The final signal equals the base model signal.")

        st.subheader("Latest market snapshot")
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Close", f"${float(latest_row['Close']):,.2f}")
        s2.metric("Latest return", f"{float(latest_row['return_1d']):.2%}")
        s3.metric("RSI 14", f"{float(latest_row['rsi_14']):.1f}")
        s4.metric("20-period volatility", f"{float(latest_row['volatility_20']):.2%}")

        s5, s6, s7, s8 = st.columns(4)
        s5.metric("MACD diff", f"{float(latest_row['macd_diff']):.4f}")
        s6.metric("ATR %", f"{float(latest_row['atr_pct']):.2%}")
        s7.metric("Bollinger position", f"{float(latest_row['bb_position']):.3f}")
        s8.metric("Primary model", selected_model_label)

        with st.expander("Show simple test split preview", expanded=False):
            st.caption("This chart is a diagnostic, not a trading signal. It compares historical close price with simple-split prediction probabilities.")
            st.plotly_chart(
                make_backtest_preview(results["test"], results["test_probabilities"], ticker),
                width="stretch",
                key=f"simple_backtest_preview_{ticker}_{selected_model_label}_{render_key}",
            )

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



def render_sentiment_section(
    sentiment_df: pd.DataFrame | None,
    sentiment_summary: dict | None,
    ticker: str,
    news_meta: dict | None = None,
    selected_sentiment_engine_label: str = "Lightweight financial lexicon",
    selected_news_source_label: str = "yfinance news, no API key",
) -> None:
    """Render recent-news sentiment analysis."""
    news_meta = news_meta or {}
    with sentiment_placeholder.container():
        st.subheader("News sentiment")
        company_name = str(news_meta.get("company_name") or ticker.upper())
        aliases = news_meta.get("company_aliases") or []
        if sentiment_summary is not None and sentiment_summary.get("available"):
            headline_count = int(sentiment_summary.get("headline_count", 0) or 0)
            overall_label = sentiment_summary.get("overall_label", "Unknown")
            avg_score = float(sentiment_summary.get("average_score", 0.0) or 0.0)
            confidence = float(sentiment_summary.get("confidence", 0.0) or 0.0)
            st.write(
                f"Meroq scored **{headline_count} company-relevant headlines** for "
                f"**{company_name} ({ticker.upper()})**. Current news tone is **{overall_label}** "
                f"with an average sentiment score of **{avg_score:+.2f}** and confidence of **{confidence:.1%}**."
            )
            if aliases:
                st.caption("Company matching used: " + ", ".join(str(a) for a in aliases[:5]))
        else:
            st.write(
                "Recent-news sentiment will appear here after headlines are fetched and scored. "
                "Meroq can use yfinance, optional user-provided news API keys, and local Hugging Face models."
            )

        with st.expander("Sentiment engine availability", expanded=False):
            st.dataframe(sentiment_engine_availability(), width="stretch", hide_index=True)
            st.caption("Hugging Face models run locally after the first download. Install dependencies with `python -m pip install -r requirements.txt`.")

        source_used = news_meta.get("source_used", "none")
        source_note = f"Requested source: {selected_news_source_label}. Used source: {source_used}."
        if news_meta.get("fallback_used"):
            source_note += " Fallback was used."
        if news_meta.get("notes"):
            source_note += " " + " ".join(str(x) for x in news_meta.get("notes", []))
        st.caption(source_note)
        if news_meta.get("newsapi_query"):
            with st.expander("News matching details", expanded=False):
                st.write(f"Company resolved as: **{company_name}**")
                st.write("NewsAPI query used:")
                st.code(str(news_meta.get("newsapi_query")), language="text")
                st.write(str(news_meta.get("relevance_filter", "Company relevance filter enabled.")))
        st.caption(f"Sentiment engine selected: {selected_sentiment_engine_label}")

        if sentiment_summary is None or not sentiment_summary.get("available"):
            st.info("No recent headlines were returned or sentiment analysis was skipped.")
            st.write("The model, chart, backtest, and risk simulation still work without news sentiment.")
            return

        st.info(sentiment_context_sentence(sentiment_summary))

        a, b, c, d = st.columns(4)
        a.metric("Overall sentiment", sentiment_summary["overall_label"], f"{sentiment_summary['average_score']:+.2f}")
        b.metric("Headlines analyzed", sentiment_summary["headline_count"])
        c.metric("Positive / negative", f"{sentiment_summary['positive_count']} / {sentiment_summary['negative_count']}")
        d.metric("Avg confidence", f"{sentiment_summary['confidence']:.1%}")

        e, f, g, h = st.columns(4)
        e.metric("Source used", str(sentiment_summary.get("source_used", source_used)).title())
        f.metric("Engine", str(sentiment_summary.get("engine", "unknown")).replace("_", " ").title())
        agreement = sentiment_summary.get("agreement")
        g.metric("Model agreement", "N/A" if agreement is None else f"{agreement:.1%}")
        h.metric("Fallback used", "Yes" if news_meta.get("fallback_used") else "No")

        left, right = st.columns([1, 2])
        with left:
            st.plotly_chart(
                make_sentiment_label_chart(sentiment_df, ticker),
                width="stretch",
                key=f"sentiment_mix_{ticker}_{sentiment_summary['headline_count']}_{sentiment_summary.get('engine')}_{source_used}",
            )
        with right:
            st.plotly_chart(
                make_sentiment_timeline_chart(sentiment_df, ticker),
                width="stretch",
                key=f"sentiment_timeline_{ticker}_{sentiment_summary['headline_count']}_{sentiment_summary.get('engine')}_{source_used}",
            )

        st.plotly_chart(
            make_sentiment_score_chart(sentiment_df, ticker),
            width="stretch",
            key=f"sentiment_scores_{ticker}_{sentiment_summary['headline_count']}_{sentiment_summary.get('engine')}_{source_used}",
        )

        show_cols = [
            "published_at",
            "source",
            "publisher",
            "sentiment_label",
            "sentiment_score",
            "confidence",
            "positive_probability",
            "neutral_probability",
            "negative_probability",
            "model_agreement",
            "sentiment_engine_detail",
            "title",
            "url",
        ]
        existing_cols = [col for col in show_cols if col in sentiment_df.columns]
        daily_sentiment = aggregate_daily_sentiment(sentiment_df, ticker=ticker)
        if not daily_sentiment.empty:
            try:
                save_daily_sentiment_features(
                    daily_sentiment,
                    ticker=ticker,
                    engine=str(sentiment_summary.get("engine", "unknown")),
                    source_used=str(sentiment_summary.get("source_used", news_meta.get("source_used", "unknown"))),
                )
            except Exception:
                pass
        with st.expander("Daily sentiment features", expanded=False):
            if daily_sentiment.empty:
                st.info("No daily sentiment features were created from the current headline set.")
            else:
                st.dataframe(daily_sentiment, width="stretch", hide_index=True)
                st.caption("These aggregated daily fields are the basis for the next modeling step: joining sentiment to OHLCV rows.")

        with st.expander("Headline-level sentiment table", expanded=False):
            st.dataframe(sentiment_df[existing_cols], width="stretch", hide_index=True)

        st.caption(
            "Safety: no paid inference API is used. Optional Finnhub/NewsAPI keys are free-plan inputs only, read from local `.env`, and never committed."
        )

def render_sentiment_modeling_section(
    model_frame: pd.DataFrame,
    sentiment_df: pd.DataFrame | None,
    ticker: str,
    selected_model_name: str,
    selected_model_label: str,
    run_experiment: bool,
    lag_days: int = 1,
) -> None:
    with sentiment_modeling_placeholder.container():
        st.subheader("Sentiment-aware modeling readiness")
        st.write(
            "This section checks whether cached news sentiment is ready to become a historical model feature. "
            "It is intentionally conservative and uses lagged sentiment to reduce look-ahead bias."
        )

        current_daily_sentiment = aggregate_daily_sentiment(sentiment_df, ticker=ticker)
        stored_daily_sentiment = load_daily_sentiment_features(ticker=ticker)
        daily_sentiment = merge_daily_sentiment_frames([stored_daily_sentiment, current_daily_sentiment])

        readiness = analyze_sentiment_modeling_readiness(
            model_frame,
            daily_sentiment,
            min_aligned_rows=30,
            lag_days=int(lag_days),
        )
        readiness_df = pd.DataFrame([readiness.as_dict()])

        a, b, c, d = st.columns(4)
        a.metric("Model rows", readiness.total_model_rows)
        b.metric("Aligned sentiment rows", readiness.aligned_sentiment_rows)
        c.metric("Sentiment coverage", f"{readiness.sentiment_coverage:.1%}")
        d.metric("Ready", "Yes" if readiness.ready_for_experiment else "Not yet")

        st.info(readiness.note)

        with st.expander("Readiness details", expanded=False):
            st.dataframe(readiness_df, width="stretch", hide_index=True)
            st.write(
                {
                    "current_run_daily_rows": int(len(current_daily_sentiment)),
                    "stored_daily_rows": int(len(stored_daily_sentiment)),
                    "merged_daily_rows": int(len(daily_sentiment)),
                    "lag_days": int(lag_days),
                }
            )

        with st.expander("Why this is conservative", expanded=False):
            st.write(
                "Meroq uses lagged daily sentiment features by default. This helps reduce look-ahead bias because same-day news "
                "may be published after market close. The experiment becomes more meaningful as the local sentiment feature store grows."
            )

        if not run_experiment:
            st.info(
                "The modeling experiment is turned off. Enable **Run sentiment modeling experiment** under Signal fusion if you want the diagnostic comparison."
            )
            if not daily_sentiment.empty:
                with st.expander("Daily sentiment feature sample", expanded=False):
                    st.dataframe(daily_sentiment.head(20), width="stretch", hide_index=True)
            return

        try:
            experiment = compare_base_vs_sentiment_simple_split(
                model_frame=model_frame,
                daily_sentiment=daily_sentiment,
                model_name=selected_model_name,
                lag_days=int(lag_days),
                n_estimators=120,
            )
        except Exception as exc:
            st.error(f"Sentiment modeling experiment failed: {exc}")
            return

        st.subheader("Technical-only vs. technical + sentiment")
        if not experiment.get("available"):
            st.warning(experiment.get("reason", "The experiment is not available yet."))
        else:
            comparison = experiment["comparison"].copy()
            metric_cols = ["accuracy", "precision", "recall", "f1", "roc_auc"]
            for col in metric_cols:
                if col in comparison.columns:
                    comparison[col] = comparison[col].astype(float)
            st.dataframe(comparison, width="stretch", hide_index=True)
            if not experiment.get("ready_for_experiment"):
                st.warning(
                    "This comparison is an early research diagnostic. Treat it cautiously until Meroq has more aligned historical sentiment rows."
                )

        with st.expander("Sentiment feature preview", expanded=False):
            preview = experiment.get("sentiment_feature_preview")
            if isinstance(preview, pd.DataFrame) and not preview.empty:
                st.dataframe(preview, width="stretch", hide_index=True)
            else:
                st.info("No sentiment feature preview is available yet.")

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
        st.subheader("Local data layer")
        st.write(
            "Meroq stores generated market and news data locally so repeat runs are faster, easier to inspect, "
            "and less dependent on repeated API calls."
        )

        st.subheader("Database files")
        st.dataframe(database_file_summary(), width="stretch", hide_index=True)

        st.subheader("Market data inventory")
        market_inventory = inspect_market_database()
        if not market_inventory.empty:
            st.dataframe(market_inventory, width="stretch", hide_index=True)
        else:
            st.info("No saved market tables found yet. Running the app or the refresh script will create them.")

        st.subheader("News cache inventory")
        news_inventory = inspect_news_cache()
        if not news_inventory.empty:
            st.dataframe(news_inventory, width="stretch", hide_index=True)
        else:
            st.info("No cached news rows found yet. Run News Sentiment with local caching enabled to create the cache.")

        st.subheader("Daily sentiment feature inventory")
        sentiment_inventory = inspect_sentiment_features()
        if not sentiment_inventory.empty:
            st.dataframe(sentiment_inventory, width="stretch", hide_index=True)
        else:
            st.info("No daily sentiment feature rows found yet. Run News Sentiment or scripts/refresh_sentiment_features.py to create them.")

        saved_tables = list_saved_price_tables()
        if saved_tables:
            with st.expander("Raw saved price table names", expanded=False):
                st.code("\n".join(saved_tables))

        if raw_df is not None:
            st.subheader("Latest raw price rows")
            st.dataframe(raw_df.tail(100), width="stretch")

        if model_frame is not None:
            st.subheader("Latest model training rows")
            st.dataframe(model_frame.tail(100), width="stretch")


def render_watchlist_section(watchlist_df: pd.DataFrame | None, scan_summary: dict | None = None) -> None:
    """Render the multi-ticker watchlist intelligence view."""
    with watchlist_placeholder.container():
        st.subheader("Watchlist intelligence")
        st.write(
            "Scan a small universe to compare model probability, recent sentiment, trend, and risk in one table. "
            "This is meant for idea discovery, not automated trading."
        )

        if watchlist_df is None or watchlist_df.empty:
            st.info("Watchlist scan was skipped. Enable **Run watchlist intelligence scan** in the sidebar.")
            return

        summary = scan_summary or summarize_watchlist_scan(watchlist_df)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tickers scanned", summary.get("tickers_scanned", 0))
        c2.metric("Bullish names", summary.get("bullish_count", 0))
        c3.metric("Positive sentiment", summary.get("positive_sentiment_count", 0))
        c4.metric("High-risk names", summary.get("high_risk_count", 0))

        ok_df = watchlist_df[watchlist_df["status"] == "ok"].copy()
        if ok_df.empty:
            st.warning("No watchlist tickers completed successfully. Check Run Details for errors.")
            st.dataframe(watchlist_df, width="stretch", hide_index=True)
            return

        top_df = ok_df.sort_values("meroq_score", ascending=False).head(10)
        display_cols = [
            "ticker",
            "latest_close",
            "return_1d",
            "base_signal",
            "base_up_probability",
            "sentiment_label",
            "sentiment_score",
            "final_signal",
            "final_up_probability",
            "risk_label",
            "risk_positive_probability",
            "risk_loss_gt_5pct",
            "meroq_score",
        ]
        display_cols = [c for c in display_cols if c in ok_df.columns]

        st.markdown("### Ranked scan")
        st.dataframe(
            ok_df.sort_values("meroq_score", ascending=False)[display_cols],
            width="stretch",
            hide_index=True,
        )

        left, right = st.columns(2)
        with left:
            st.plotly_chart(
                px.bar(
                    top_df.sort_values("meroq_score"),
                    x="meroq_score",
                    y="ticker",
                    orientation="h",
                    title="Top Meroq scores",
                    range_x=[0, 100],
                ),
                width="stretch",
                key="watchlist_score_bar_v90",
            )
        with right:
            st.plotly_chart(
                px.scatter(
                    ok_df,
                    x="risk_loss_gt_5pct",
                    y="final_up_probability",
                    size="meroq_score",
                    hover_name="ticker",
                    title="Probability vs. downside risk",
                    labels={
                        "risk_loss_gt_5pct": "P(loss > 5%)",
                        "final_up_probability": "Final up probability",
                    },
                ),
                width="stretch",
                key="watchlist_risk_probability_scatter_v90",
            )

        st.markdown("### Quick read")
        bullish = ok_df.sort_values("meroq_score", ascending=False).head(3)["ticker"].tolist()
        cautious = ok_df.sort_values("risk_loss_gt_5pct", ascending=False).head(3)["ticker"].tolist()
        uncertainty_order = (ok_df["final_up_probability"] - 0.5).abs().sort_values().index
        uncertain = ok_df.loc[uncertainty_order].head(3)["ticker"].tolist()
        st.write(f"**Highest-ranked:** {', '.join(bullish) if bullish else 'N/A'}")
        st.write(f"**Highest downside-risk watch:** {', '.join(cautious) if cautious else 'N/A'}")
        st.write(f"**Most uncertain:** {', '.join(uncertain) if uncertain else 'N/A'}")

        failed_df = watchlist_df[watchlist_df["status"] != "ok"]
        if not failed_df.empty:
            with st.expander("Failed/skipped ticker details", expanded=False):
                st.dataframe(failed_df, width="stretch", hide_index=True)


def render_report_section(
    ticker: str,
    latest_close: float,
    latest_date,
    analysis_mode: str,
    selected_model_label: str,
    prediction: dict,
    results: dict,
    sentiment_fusion: dict | None,
    sentiment_summary: dict | None,
    risk_results: dict | None,
    watchlist_df: pd.DataFrame | None,
    simple_comparison: pd.DataFrame | None,
    wf_results: dict | None,
) -> None:
    """Render an exportable run report."""
    with report_placeholder.container():
        st.subheader("Meroq insight report")
        st.write(
            "Generate a concise Markdown report from the current run. "
            "Use it for notes, project documentation, or sharing analysis output."
        )

        report_markdown = build_insight_report(
            ticker=ticker,
            latest_close=latest_close,
            latest_date=str(latest_date),
            analysis_mode=analysis_mode,
            selected_model_label=selected_model_label,
            prediction=prediction,
            model_metrics=results.get("metrics", {}),
            sentiment_fusion=sentiment_fusion,
            sentiment_summary=sentiment_summary,
            risk_summary=risk_results.get("summary") if risk_results else None,
            watchlist_df=watchlist_df,
            model_comparison_df=simple_comparison,
            walk_forward_results=wf_results,
        )

        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.download_button(
                "Download Markdown report",
                data=report_markdown,
                file_name=f"meroq_{ticker.upper()}_report.md",
                mime="text/markdown",
                key=f"download_report_{ticker}_{selected_model_label}",
                width="stretch",
            )
        with col_b:
            st.caption("The report includes the latest signal, sentiment overlay, risk simulation, watchlist highlights, and model comparison summary.")

        with st.expander("Preview report", expanded=True):
            st.markdown(report_markdown)

        if watchlist_df is not None and not watchlist_df.empty:
            csv_data = watchlist_df.to_csv(index=False)
            st.download_button(
                "Download watchlist scan CSV",
                data=csv_data,
                file_name="meroq_watchlist_scan.csv",
                mime="text/csv",
                key=f"download_watchlist_csv_{ticker}_{selected_model_label}",
                width="stretch",
            )


def render_roadmap_section() -> None:
    with roadmap_placeholder.container():
        st.subheader("Production-minded upgrade path")
        st.markdown(
            """
            **Current release: 1.0.1 — Company-aware news matching and exportable insight reports.**

            This release adds a multi-ticker intelligence layer and a downloadable report workflow:

            1. Scans a configurable watchlist with a fast local model.
            2. Combines model probability, recent-news sentiment, trend, and risk into a transparent Meroq Score.
            3. Shows ranked candidates, high-risk names, and uncertain names.
            4. Keeps advanced walk-forward and model-comparison tools optional so the app remains responsive.

            Next production-minded upgrades:

            1. Exportable single-ticker and watchlist reports.
            2. A cleaner landing page and public demo configuration.
            3. Portfolio-level risk views.
            4. Scheduled local refresh tasks for prices/news/sentiment.
            5. PostgreSQL if deployment/data scale needs grow.
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
with watchlist_placeholder.container():
    st.info("Waiting for watchlist scan settings...")
with report_placeholder.container():
    st.info("Report will be generated after the main analysis finishes.")
with chart_placeholder.container():
    st.info("Waiting for price chart...")
with risk_placeholder.container():
    st.info("Waiting for risk simulation...")
with sentiment_placeholder.container():
    st.info("Waiting for news sentiment...")
update_run_monitor("Sentiment-aware signal", "waiting", "Waiting for news sentiment", 0)
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
    render_summary_metrics(ticker, latest_close, latest_date, selected_model_label, prediction, results, None, risk_results=None, sentiment_summary=None, analysis_mode=analysis_mode)
    render_prediction_section(latest_row, prediction, results, ticker, selected_model_label, render_key="base")

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

    sentiment_df = pd.DataFrame()
    sentiment_summary = summarize_sentiment(sentiment_df)
    news_meta = {"source_used": "none"}
    if run_sentiment_analysis:
        update_run_monitor(
            "News sentiment",
            "running",
            f"Fetching up to {max_news_items} headlines for {ticker} via {selected_news_source_label}",
            50,
        )
        news_df, news_meta = fetch_news_for_ticker(
            ticker=ticker,
            source=selected_news_source,
            max_items=int(max_news_items),
            days_back=int(news_lookback_days),
            use_cache=bool(cache_news_locally),
            force_refresh=bool(force_news_refresh),
        )
        update_run_monitor(
            "News sentiment",
            "running",
            f"Scoring {len(news_df):,} headlines with {selected_sentiment_engine_label}",
            51,
        )
        sentiment_df = analyze_news_sentiment(news_df, engine=selected_sentiment_engine)
        sentiment_summary = summarize_sentiment(sentiment_df)
        if sentiment_summary.get("available"):
            update_run_monitor(
                "News sentiment",
                "complete",
                f"{sentiment_summary['headline_count']} headlines; {sentiment_summary['overall_label']} overall",
                52,
                f"News sentiment complete: {sentiment_summary['overall_label']} average score {sentiment_summary['average_score']:+.2f} across {sentiment_summary['headline_count']} headlines.",
            )
        else:
            update_run_monitor(
                "News sentiment",
                "complete",
                "No recent headlines returned",
                52,
                "News sentiment: no recent headlines were returned, so price/model/risk results remain the primary analysis.",
            )
    else:
        update_run_monitor("News sentiment", "skipped", "Skipped in sidebar", 52)

    render_sentiment_section(
        sentiment_df,
        sentiment_summary,
        ticker,
        news_meta=news_meta,
        selected_sentiment_engine_label=selected_sentiment_engine_label,
        selected_news_source_label=selected_news_source_label,
    )

    update_run_monitor(
        "Sentiment modeling",
        "running" if run_sentiment_modeling_experiment else "skipped",
        "Checking lagged sentiment feature readiness" if run_sentiment_modeling_experiment else "Experiment disabled in sidebar",
        52,
    )
    render_sentiment_modeling_section(
        model_frame=model_frame,
        sentiment_df=sentiment_df,
        ticker=ticker,
        selected_model_name=selected_model_name,
        selected_model_label=selected_model_label,
        run_experiment=bool(run_sentiment_modeling_experiment),
        lag_days=int(sentiment_model_lag_days),
    )
    update_run_monitor(
        "Sentiment modeling",
        "complete" if run_sentiment_modeling_experiment else "skipped",
        "Sentiment modeling readiness displayed" if run_sentiment_modeling_experiment else "Skipped for speed",
        53,
    )

    sentiment_fusion = None
    if run_sentiment_fusion and run_sentiment_analysis:
        update_run_monitor(
            "Sentiment-aware signal",
            "running",
            "Blending base model probability with recent-news sentiment",
            53,
        )
        sentiment_fusion = fuse_prediction_with_sentiment(
            prediction,
            sentiment_summary,
            max_adjustment=float(sentiment_max_adjustment),
        )
        if sentiment_fusion.get("available"):
            update_run_monitor(
                "Sentiment-aware signal",
                "complete",
                f"{sentiment_fusion['base_up_probability']:.1%} → {sentiment_fusion['adjusted_up_probability']:.1%}",
                55,
                f"Sentiment-aware signal: {sentiment_fusion['base_signal']} base signal became {sentiment_fusion['signal']} after a {sentiment_fusion['adjustment_pct_points']:+.2f} percentage-point sentiment adjustment.",
            )
        else:
            update_run_monitor(
                "Sentiment-aware signal",
                "skipped",
                "No usable sentiment overlay available",
                55,
            )
    else:
        update_run_monitor(
            "Sentiment-aware signal",
            "skipped",
            "Disabled in sidebar or news sentiment skipped",
            55,
        )

    render_prediction_section(latest_row, prediction, results, ticker, selected_model_label, sentiment_fusion=sentiment_fusion, render_key="final")
    render_summary_metrics(
        ticker,
        latest_close,
        latest_date,
        selected_model_label,
        prediction,
        results,
        None,
        risk_results=risk_results,
        sentiment_summary=sentiment_summary,
        sentiment_fusion=sentiment_fusion,
        analysis_mode=analysis_mode,
    )

    watchlist_df = pd.DataFrame()
    watchlist_summary = {}
    if run_watchlist_scan:
        parsed_watchlist = [x.strip().upper() for x in watchlist_text.replace("\n", ",").split(",") if x.strip()]
        parsed_watchlist = list(dict.fromkeys(parsed_watchlist))[: int(watchlist_max_tickers)]
        update_run_monitor(
            "Watchlist scan",
            "running",
            f"Scanning {len(parsed_watchlist)} tickers",
            56,
        )
        watchlist_df = scan_watchlist(
            tickers=parsed_watchlist,
            period=period,
            interval=interval,
            news_source=selected_news_source,
            sentiment_engine=selected_sentiment_engine,
            max_news_items=min(int(max_news_items), 10),
            days_back=int(news_lookback_days),
            include_sentiment=bool(watchlist_include_sentiment and run_sentiment_analysis),
            include_risk=bool(watchlist_include_risk and run_risk_simulation),
            risk_horizon=min(int(simulation_horizon), 30),
            risk_paths=min(int(simulation_paths), 500),
            volatility_window=int(volatility_window),
            drift_mode=drift_mode,
            max_adjustment=float(sentiment_max_adjustment),
            progress_callback=lambda payload: update_run_monitor(
                "Watchlist scan",
                "running" if payload.get("status") in {"running", "complete"} and int(payload.get("index", 0) or 0) < int(payload.get("total", 1) or 1) else payload.get("status", "running"),
                f"{payload.get('ticker', 'ticker')} ({payload.get('index', 0)}/{payload.get('total', 0)}): {payload.get('detail', payload.get('status', ''))}",
                56 + int(9 * (int(payload.get("index", 0) or 0) / max(1, int(payload.get("total", 1) or 1)))),
            ),
        )
        watchlist_summary = summarize_watchlist_scan(watchlist_df)
        update_run_monitor(
            "Watchlist scan",
            "complete",
            f"Scanned {watchlist_summary.get('tickers_scanned', 0)} tickers",
            65,
            f"Watchlist scan complete: {watchlist_summary.get('bullish_count', 0)} bullish names and {watchlist_summary.get('high_risk_count', 0)} high-risk names.",
        )
    else:
        update_run_monitor("Watchlist scan", "skipped", "Skipped in sidebar", 65)

    render_watchlist_section(watchlist_df, watchlist_summary)

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

    render_summary_metrics(
        ticker,
        latest_close,
        latest_date,
        selected_model_label,
        prediction,
        results,
        wf_results,
        risk_results=risk_results,
        sentiment_summary=sentiment_summary,
        sentiment_fusion=sentiment_fusion,
        analysis_mode=analysis_mode,
    )
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


    render_report_section(
        ticker=ticker,
        latest_close=latest_close,
        latest_date=latest_date,
        analysis_mode=analysis_mode,
        selected_model_label=selected_model_label,
        prediction=prediction,
        results=results,
        sentiment_fusion=sentiment_fusion,
        sentiment_summary=sentiment_summary,
        risk_results=risk_results,
        watchlist_df=watchlist_df,
        simple_comparison=simple_comparison,
        wf_results=wf_results,
    )

    update_run_monitor(
        "Dashboard tabs",
        "complete",
        "All result sections are ready",
        100,
        "Dashboard is ready: Prediction, Watchlist, Report, Chart, Risk Simulation, News Sentiment, Sentiment Modeling, Backtest, Model Comparison, Model Details, Data Manager, and Roadmap sections are loaded.",
    )

except Exception as exc:
    update_run_monitor("Dashboard tabs", "failed", str(exc), 100)
    with summary_placeholder.container():
        st.error(f"Something went wrong: {exc}")
    st.stop()
