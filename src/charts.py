from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def _chart_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Create a chart-safe copy with numeric price columns."""
    data = df.copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")

    numeric_cols = ["Open", "High", "Low", "Close", "sma_20", "sma_50"]
    for col in numeric_cols:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    return data.dropna(subset=["Date", "Open", "High", "Low", "Close"])


def make_price_chart(feature_df: pd.DataFrame, ticker: str) -> go.Figure:
    """Create candlestick chart with SMA overlays."""
    data = _chart_frame(feature_df)
    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=data["Date"],
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name="OHLC",
        )
    )

    for col, name in [("sma_20", "SMA 20"), ("sma_50", "SMA 50")]:
        if col in data.columns:
            fig.add_trace(go.Scatter(x=data["Date"], y=data[col], mode="lines", name=name))

    fig.update_layout(
        title=f"{ticker.upper()} Price Chart",
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        height=600,
    )
    return fig


def make_probability_gauge(up_probability: float) -> go.Figure:
    """Create probability indicator."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=up_probability * 100,
            number={"suffix": "%"},
            title={"text": "Predicted probability of next-period upward move"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"thickness": 0.3},
                "steps": [
                    {"range": [0, 45]},
                    {"range": [45, 55]},
                    {"range": [55, 100]},
                ],
            },
        )
    )
    fig.update_layout(height=350)
    return fig


def make_feature_importance_chart(feature_importance: pd.DataFrame, top_n: int = 12):
    """Plot top feature importances."""
    top = feature_importance.head(top_n).sort_values("importance", ascending=True)
    fig = px.bar(
        top,
        x="importance",
        y="feature",
        orientation="h",
        title=f"Top {top_n} Feature Importances / Coefficients",
    )
    fig.update_layout(height=500)
    return fig


def make_backtest_preview(test_df: pd.DataFrame, probabilities, ticker: str) -> go.Figure:
    """Simple visual comparing close price and predicted up probability."""
    data = test_df.copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data["Close"] = pd.to_numeric(data["Close"], errors="coerce")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data["Date"], y=data["Close"], mode="lines", name="Close", yaxis="y1"))
    fig.add_trace(
        go.Scatter(x=data["Date"], y=probabilities, mode="lines", name="Predicted Up Probability", yaxis="y2")
    )

    fig.update_layout(
        title=f"{ticker.upper()} Simple Test Split: Close vs Prediction Probability",
        xaxis={"title": "Date"},
        yaxis={"title": "Close Price"},
        yaxis2={"title": "Up Probability", "overlaying": "y", "side": "right", "range": [0, 1]},
        height=500,
    )
    return fig


def make_equity_curve_chart(predictions: pd.DataFrame, ticker: str) -> go.Figure:
    """Plot buy-and-hold, long-only, and long-short equity curves."""
    data = predictions.copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")

    fig = go.Figure()
    for col, name in [
        ("market_equity", "Buy & Hold"),
        ("long_equity", "Model Long-Only"),
        ("long_short_equity", "Model Long/Short"),
    ]:
        if col in data.columns:
            fig.add_trace(go.Scatter(x=data["Date"], y=data[col], mode="lines", name=name))

    fig.update_layout(
        title=f"{ticker.upper()} Walk-Forward Equity Curves",
        xaxis_title="Date",
        yaxis_title="Growth of $1",
        height=520,
    )
    return fig


def make_probability_backtest_chart(predictions: pd.DataFrame, ticker: str) -> go.Figure:
    """Plot close price and walk-forward probabilities."""
    data = predictions.copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data["Close"] = pd.to_numeric(data["Close"], errors="coerce")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data["Date"], y=data["Close"], mode="lines", name="Close", yaxis="y1"))
    fig.add_trace(
        go.Scatter(x=data["Date"], y=data["proba_up"], mode="lines", name="Walk-Forward Up Probability", yaxis="y2")
    )

    fig.update_layout(
        title=f"{ticker.upper()} Walk-Forward Probability vs Price",
        xaxis={"title": "Date"},
        yaxis={"title": "Close Price"},
        yaxis2={"title": "Up Probability", "overlaying": "y", "side": "right", "range": [0, 1]},
        height=520,
    )
    return fig


def make_drawdown_chart(predictions: pd.DataFrame) -> go.Figure:
    """Plot drawdowns for equity curves."""
    data = predictions.copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")

    fig = go.Figure()
    for col, name in [
        ("market_equity", "Buy & Hold Drawdown"),
        ("long_equity", "Long-Only Drawdown"),
        ("long_short_equity", "Long/Short Drawdown"),
    ]:
        if col in data.columns:
            equity = pd.to_numeric(data[col], errors="coerce")
            drawdown = equity / equity.cummax() - 1
            fig.add_trace(go.Scatter(x=data["Date"], y=drawdown, mode="lines", name=name))

    fig.update_layout(title="Drawdown", xaxis_title="Date", yaxis_title="Drawdown", height=420)
    fig.update_yaxes(tickformat=".0%")
    return fig


def make_model_metric_bar_chart(summary: pd.DataFrame, metric: str, title: str) -> go.Figure:
    """Compare models using one numeric metric."""
    data = summary.copy()
    if metric not in data.columns:
        fig = go.Figure()
        fig.update_layout(title=f"Missing metric: {metric}")
        return fig

    data[metric] = pd.to_numeric(data[metric], errors="coerce")
    data = data.dropna(subset=[metric])
    fig = px.bar(data, x="model", y=metric, title=title, text=metric)
    fig.update_traces(texttemplate="%{text:.3f}", textposition="outside")
    fig.update_layout(height=420, xaxis_title="Model", yaxis_title=metric.replace("_", " ").title())
    return fig


def make_walk_forward_model_return_chart(summary: pd.DataFrame) -> go.Figure:
    """Compare walk-forward strategy returns by model."""
    data = summary.copy()
    cols = ["model", "long_total_return", "long_short_total_return"]
    for col in cols[1:]:
        if col not in data.columns:
            data[col] = 0.0
        data[col] = pd.to_numeric(data[col], errors="coerce")

    long_df = data[["model", "long_total_return"]].rename(columns={"long_total_return": "return"})
    long_df["strategy"] = "Long-only"
    ls_df = data[["model", "long_short_total_return"]].rename(columns={"long_short_total_return": "return"})
    ls_df["strategy"] = "Long/short"
    chart_df = pd.concat([long_df, ls_df], ignore_index=True).dropna(subset=["return"])

    fig = px.bar(chart_df, x="model", y="return", color="strategy", barmode="group", title="Walk-Forward Strategy Returns by Model")
    fig.update_layout(height=460, xaxis_title="Model", yaxis_title="Total Return")
    fig.update_yaxes(tickformat=".0%")
    return fig


def make_monte_carlo_percentile_chart(percentiles: pd.DataFrame, ticker: str) -> go.Figure:
    """Plot Monte Carlo percentile fan chart."""
    data = percentiles.copy()
    for col in ["step", "p05", "p10", "p25", "p50", "p75", "p90", "p95"]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    fig = go.Figure()
    for col, name in [
        ("p05", "5th percentile"),
        ("p10", "10th percentile"),
        ("p25", "25th percentile"),
        ("p50", "Median"),
        ("p75", "75th percentile"),
        ("p90", "90th percentile"),
        ("p95", "95th percentile"),
    ]:
        if col in data.columns:
            fig.add_trace(go.Scatter(x=data["step"], y=data[col], mode="lines", name=name))

    fig.update_layout(
        title=f"{ticker.upper()} Monte Carlo Price Range",
        xaxis_title="Future period",
        yaxis_title="Simulated price",
        height=520,
    )
    return fig


def make_monte_carlo_sample_paths_chart(paths: pd.DataFrame, ticker: str, max_paths: int = 80) -> go.Figure:
    """Plot a limited sample of simulated price paths."""
    data = paths.copy()
    data["step"] = pd.to_numeric(data["step"], errors="coerce")

    path_cols = [col for col in data.columns if col != "step"][:max_paths]
    fig = go.Figure()
    for col in path_cols:
        fig.add_trace(
            go.Scatter(
                x=data["step"],
                y=pd.to_numeric(data[col], errors="coerce"),
                mode="lines",
                showlegend=False,
                opacity=0.18,
                line={"width": 1},
            )
        )

    fig.update_layout(
        title=f"{ticker.upper()} Sample Simulated Paths",
        xaxis_title="Future period",
        yaxis_title="Simulated price",
        height=460,
    )
    return fig


def make_final_return_distribution_chart(final_distribution: pd.DataFrame, ticker: str) -> go.Figure:
    """Plot distribution of final simulated returns."""
    data = final_distribution.copy()
    data["final_return"] = pd.to_numeric(data["final_return"], errors="coerce")
    fig = px.histogram(
        data.dropna(subset=["final_return"]),
        x="final_return",
        nbins=50,
        title=f"{ticker.upper()} Simulated Final Return Distribution",
    )
    fig.update_layout(height=460, xaxis_title="Final return", yaxis_title="Simulation count")
    fig.update_xaxes(tickformat=".0%")
    return fig


def make_sentiment_label_chart(sentiment_df: pd.DataFrame, ticker: str) -> go.Figure:
    """Plot headline count by sentiment label."""
    if sentiment_df is None or sentiment_df.empty or "sentiment_label" not in sentiment_df.columns:
        fig = go.Figure()
        fig.update_layout(title=f"{ticker.upper()} News Sentiment Mix", height=360)
        return fig

    label_order = ["Positive", "Neutral", "Negative"]
    counts = sentiment_df["sentiment_label"].value_counts().reindex(label_order, fill_value=0).reset_index()
    counts.columns = ["sentiment_label", "headline_count"]
    fig = px.bar(
        counts,
        x="sentiment_label",
        y="headline_count",
        text="headline_count",
        title=f"{ticker.upper()} News Sentiment Mix",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(height=360, xaxis_title="Sentiment", yaxis_title="Headlines")
    return fig


def make_sentiment_score_chart(sentiment_df: pd.DataFrame, ticker: str) -> go.Figure:
    """Plot sentiment scores by recent headline."""
    if sentiment_df is None or sentiment_df.empty or "sentiment_score" not in sentiment_df.columns:
        fig = go.Figure()
        fig.update_layout(title=f"{ticker.upper()} Headline Sentiment Scores", height=480)
        return fig

    data = sentiment_df.copy().head(20)
    data["sentiment_score"] = pd.to_numeric(data["sentiment_score"], errors="coerce")
    data["headline"] = data.get("short_title", data.get("title", "")).astype(str).str.slice(0, 90)
    data = data.dropna(subset=["sentiment_score"]).iloc[::-1]

    fig = px.bar(
        data,
        x="sentiment_score",
        y="headline",
        orientation="h",
        title=f"{ticker.upper()} Recent Headline Sentiment Scores",
        hover_data=[col for col in ["publisher", "sentiment_label", "confidence"] if col in data.columns],
    )
    fig.update_layout(height=max(420, 28 * len(data) + 160), xaxis_title="Sentiment score", yaxis_title="Headline")
    fig.update_xaxes(range=[-1, 1])
    return fig


def make_sentiment_timeline_chart(sentiment_df: pd.DataFrame, ticker: str) -> go.Figure:
    """Plot daily average sentiment where dates are available."""
    if sentiment_df is None or sentiment_df.empty or "published_at" not in sentiment_df.columns:
        fig = go.Figure()
        fig.update_layout(title=f"{ticker.upper()} Sentiment Timeline", height=360)
        return fig

    data = sentiment_df.copy()
    data["published_at"] = pd.to_datetime(data["published_at"], errors="coerce")
    data["sentiment_score"] = pd.to_numeric(data["sentiment_score"], errors="coerce")
    data = data.dropna(subset=["published_at", "sentiment_score"])
    if data.empty:
        fig = go.Figure()
        fig.update_layout(title=f"{ticker.upper()} Sentiment Timeline", height=360)
        return fig

    data["date"] = data["published_at"].dt.date
    daily = data.groupby("date", as_index=False).agg(avg_sentiment=("sentiment_score", "mean"), headlines=("sentiment_score", "size"))
    fig = px.line(daily, x="date", y="avg_sentiment", markers=True, title=f"{ticker.upper()} Daily Average News Sentiment")
    fig.update_layout(height=360, xaxis_title="Date", yaxis_title="Average sentiment")
    fig.update_yaxes(range=[-1, 1])
    return fig


def _future_dates_from_history(price_df: pd.DataFrame, steps: int, interval: str = "1d") -> pd.DatetimeIndex:
    """Build future display dates for forecast charts."""
    dates = pd.to_datetime(price_df.get("Date"), errors="coerce").dropna()
    if dates.empty:
        start = pd.Timestamp.today().normalize()
    else:
        start = dates.max().normalize()

    interval = str(interval).lower().strip()
    if interval == "1wk":
        return pd.date_range(start=start + pd.offsets.Week(1), periods=int(steps), freq="W-FRI")
    return pd.bdate_range(start=start + pd.offsets.BDay(1), periods=int(steps))


def make_price_forecast_chart(
    price_df: pd.DataFrame,
    percentiles: pd.DataFrame,
    ticker: str,
    interval: str = "1d",
    lookback: int = 252,
) -> go.Figure:
    """Plot historical close price with a forward-looking forecast range.

    This chart is intentionally product-facing: it shows where price has been,
    the latest close, and the simulated expected range going forward. It avoids
    model probability noise and is meant for the Prediction tab.
    """
    history = price_df.copy()
    history["Date"] = pd.to_datetime(history["Date"], errors="coerce")
    history["Close"] = pd.to_numeric(history["Close"], errors="coerce")
    history = history.dropna(subset=["Date", "Close"]).sort_values("Date")
    if lookback and lookback > 0:
        history = history.tail(int(lookback))

    forecast = percentiles.copy() if percentiles is not None else pd.DataFrame()
    for col in ["p10", "p25", "p50", "p75", "p90"]:
        if col in forecast.columns:
            forecast[col] = pd.to_numeric(forecast[col], errors="coerce")
    if "step" not in forecast.columns:
        forecast["step"] = range(1, len(forecast) + 1)
    forecast = forecast.dropna(subset=["p10", "p50", "p90"]) if {"p10", "p50", "p90"}.issubset(forecast.columns) else pd.DataFrame()

    fig = go.Figure()
    if not history.empty:
        fig.add_trace(
            go.Scatter(
                x=history["Date"],
                y=history["Close"],
                mode="lines",
                name="Historical close",
                hovertemplate="%{x|%Y-%m-%d}<br>Close: $%{y:,.2f}<extra></extra>",
            )
        )
        latest_date = history["Date"].iloc[-1]
        latest_close = float(history["Close"].iloc[-1])
        fig.add_trace(
            go.Scatter(
                x=[latest_date],
                y=[latest_close],
                mode="markers",
                name="Latest close",
                marker={"size": 10},
                hovertemplate="Latest close<br>%{x|%Y-%m-%d}<br>$%{y:,.2f}<extra></extra>",
            )
        )
    else:
        latest_date = pd.Timestamp.today().normalize()

    if not forecast.empty:
        future_dates = _future_dates_from_history(price_df, len(forecast), interval=interval)
        forecast = forecast.iloc[: len(future_dates)].copy()
        forecast["Date"] = future_dates[: len(forecast)]

        # Add high bound first and low bound second with fill between them.
        fig.add_trace(
            go.Scatter(
                x=forecast["Date"],
                y=forecast["p90"],
                mode="lines",
                name="Optimistic range",
                line={"width": 0},
                hovertemplate="%{x|%Y-%m-%d}<br>90th percentile: $%{y:,.2f}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=forecast["Date"],
                y=forecast["p10"],
                mode="lines",
                name="Likely range",
                fill="tonexty",
                line={"width": 0},
                hovertemplate="%{x|%Y-%m-%d}<br>10th percentile: $%{y:,.2f}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=forecast["Date"],
                y=forecast["p50"],
                mode="lines+markers",
                name="Expected path",
                hovertemplate="%{x|%Y-%m-%d}<br>Median forecast: $%{y:,.2f}<extra></extra>",
            )
        )

        if not history.empty:
            fig.add_vline(x=str(history["Date"].iloc[-1].date()), line_width=1, line_dash="dash")

    fig.update_layout(
        title=f"{ticker.upper()} Price History and Forecast Range",
        xaxis_title="Date",
        yaxis_title="Price",
        height=560,
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
    )
    return fig
