from __future__ import annotations

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import EMAIndicator, MACD, SMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands


BASE_NUMERIC_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def _prepare_price_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Sort data and ensure OHLCV columns are numeric."""
    data = df.copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")

    for col in BASE_NUMERIC_COLUMNS:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=["Date"] + BASE_NUMERIC_COLUMNS)
    data = data.sort_values("Date").reset_index(drop=True)
    return data


def add_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add technical indicators and price-derived features.

    This creates only features. It does not create the target column.
    """
    data = _prepare_price_frame(df)

    close = data["Close"]
    high = data["High"]
    low = data["Low"]
    open_ = data["Open"]
    volume = data["Volume"]

    data["return_1d"] = close.pct_change()
    data["log_return_1d"] = np.log(close / close.shift(1))
    data["intraday_return"] = (close - open_) / open_
    data["high_low_range"] = (high - low) / close
    data["volume_change"] = volume.pct_change()

    data["sma_5"] = SMAIndicator(close=close, window=5).sma_indicator()
    data["sma_10"] = SMAIndicator(close=close, window=10).sma_indicator()
    data["sma_20"] = SMAIndicator(close=close, window=20).sma_indicator()
    data["sma_50"] = SMAIndicator(close=close, window=50).sma_indicator()

    data["ema_12"] = EMAIndicator(close=close, window=12).ema_indicator()
    data["ema_26"] = EMAIndicator(close=close, window=26).ema_indicator()

    data["close_sma20_ratio"] = close / data["sma_20"] - 1
    data["close_sma50_ratio"] = close / data["sma_50"] - 1

    data["volatility_5"] = data["return_1d"].rolling(5).std()
    data["volatility_10"] = data["return_1d"].rolling(10).std()
    data["volatility_20"] = data["return_1d"].rolling(20).std()

    data["rsi_14"] = RSIIndicator(close=close, window=14).rsi()

    macd = MACD(close=close)
    data["macd"] = macd.macd()
    data["macd_signal"] = macd.macd_signal()
    data["macd_diff"] = macd.macd_diff()

    bb = BollingerBands(close=close, window=20, window_dev=2)
    data["bb_high"] = bb.bollinger_hband()
    data["bb_low"] = bb.bollinger_lband()
    data["bb_mid"] = bb.bollinger_mavg()
    data["bb_width"] = (data["bb_high"] - data["bb_low"]) / data["bb_mid"]
    data["bb_position"] = (close - data["bb_low"]) / (data["bb_high"] - data["bb_low"])

    atr = AverageTrueRange(high=high, low=low, close=close, window=14)
    data["atr_14"] = atr.average_true_range()
    data["atr_pct"] = data["atr_14"] / close

    stoch = StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
    data["stoch_k"] = stoch.stoch()
    data["stoch_d"] = stoch.stoch_signal()

    data = data.replace([np.inf, -np.inf], np.nan)

    return data


def add_prediction_target(feature_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create target for next-trading-day/period direction.

    target_up_tomorrow:
    1 = next close is higher than current close
    0 = next close is equal/lower than current close
    """
    data = feature_df.copy()
    data["Close"] = pd.to_numeric(data["Close"], errors="coerce")
    data["next_close"] = data["Close"].shift(-1)
    data["next_return"] = data["next_close"] / data["Close"] - 1
    data["target_up_tomorrow"] = (data["next_close"] > data["Close"]).astype(int)

    data = data.dropna(subset=["next_close", "next_return"])
    return data


def build_model_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Create feature + target table ready for ML training."""
    features = add_technical_features(df)
    model_frame = add_prediction_target(features)
    model_frame = model_frame.dropna().reset_index(drop=True)
    return model_frame
