from __future__ import annotations

from pathlib import Path
import re
import sqlite3

import pandas as pd
import yfinance as yf

from src.storage import MARKET_DB_PATH, record_price_metadata


DATA_DIR = Path("data")
DB_PATH = MARKET_DB_PATH
PRICE_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]


def _safe_table_name(ticker: str, interval: str | None = None) -> str:
    """Create a safe SQLite table name from a ticker and optional interval."""
    cleaned_ticker = re.sub(r"[^A-Za-z0-9_]", "_", ticker.upper())
    if interval:
        cleaned_interval = re.sub(r"[^A-Za-z0-9_]", "_", interval.lower())
        return f"prices_{cleaned_ticker}_{cleaned_interval}"
    return f"prices_{cleaned_ticker}"


def _flatten_yfinance_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize yfinance output.

    yfinance can return either normal columns or MultiIndex columns depending on
    version and ticker count. This function keeps price field names such as
    Open, High, Low, Close, Adj Close, and Volume.
    """
    data = df.copy()

    if isinstance(data.columns, pd.MultiIndex):
        flattened_columns: list[str] = []
        for col in data.columns:
            parts = [str(part) for part in col if str(part) not in {"", "None"}]
            price_part = next((part for part in parts if part in PRICE_COLUMNS), None)
            flattened_columns.append(price_part or "_".join(parts))
        data.columns = flattened_columns

    return data


def fetch_price_data(
    ticker: str,
    period: str = "5y",
    interval: str = "1d",
    save_to_sqlite: bool = True,
) -> pd.DataFrame:
    """
    Download historical OHLCV data from yfinance.

    Returns a DataFrame with at least:
    Date, Open, High, Low, Close, Volume
    """
    ticker = ticker.strip().upper()

    if not ticker:
        raise ValueError("Ticker cannot be empty.")

    df = yf.download(
        tickers=ticker,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=True,
    )

    if df.empty:
        raise ValueError(f"No data returned for ticker: {ticker}")

    df = _flatten_yfinance_columns(df)
    df = df.reset_index()

    if "Date" not in df.columns:
        if "Datetime" in df.columns:
            df = df.rename(columns={"Datetime": "Date"})
        elif "index" in df.columns:
            df = df.rename(columns={"index": "Date"})
        else:
            first_col = df.columns[0]
            df = df.rename(columns={first_col: "Date"})

    required_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
    missing = [col for col in required_cols if col not in df.columns]

    if missing:
        raise ValueError(
            f"Missing required columns from downloaded data: {missing}. "
            f"Available columns: {list(df.columns)}"
        )

    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.tz_localize(None)

    for col in PRICE_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=required_cols).copy()
    df = df.sort_values("Date").reset_index(drop=True)

    if save_to_sqlite:
        save_prices_to_sqlite(df, ticker=ticker, interval=interval, period=period)

    return df


def save_prices_to_sqlite(
    df: pd.DataFrame,
    ticker: str,
    interval: str = "1d",
    period: str | None = None,
    db_path: Path = DB_PATH,
) -> None:
    """Save price data to a local SQLite database and record refresh metadata."""
    DATA_DIR.mkdir(exist_ok=True)
    table_name = _safe_table_name(ticker, interval)

    with sqlite3.connect(db_path) as conn:
        df.to_sql(table_name, conn, if_exists="replace", index=False)

    record_price_metadata(
        table_name=table_name,
        ticker=ticker,
        interval=interval,
        period=period,
        df=df,
        db_path=db_path,
    )


def load_prices_from_sqlite(
    ticker: str,
    interval: str = "1d",
    db_path: Path = DB_PATH,
) -> pd.DataFrame:
    """Load saved price data from SQLite."""
    table_name = _safe_table_name(ticker, interval)

    with sqlite3.connect(db_path) as conn:
        return pd.read_sql(f"SELECT * FROM {table_name}", conn, parse_dates=["Date"])


def list_saved_price_tables(db_path: Path = DB_PATH) -> list[str]:
    """Return saved SQLite price table names."""
    if not db_path.exists():
        return []

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'prices_%' ORDER BY name"
        ).fetchall()

    return [row[0] for row in rows]
