from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import sqlite3
from typing import Any

import pandas as pd


DATA_DIR = Path("data")
MARKET_DB_PATH = DATA_DIR / "market_data.sqlite"
NEWS_CACHE_DB_PATH = DATA_DIR / "news_cache.sqlite"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(exist_ok=True)


def _connect(db_path: Path) -> sqlite3.Connection:
    ensure_data_dir()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def database_file_summary() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name, path in [("market_data", MARKET_DB_PATH), ("news_cache", NEWS_CACHE_DB_PATH)]:
        if path.exists():
            rows.append(
                {
                    "database": name,
                    "path": str(path),
                    "exists": True,
                    "size_mb": round(path.stat().st_size / (1024 * 1024), 3),
                    "modified": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
        else:
            rows.append(
                {
                    "database": name,
                    "path": str(path),
                    "exists": False,
                    "size_mb": 0.0,
                    "modified": None,
                }
            )
    return pd.DataFrame(rows)


def sqlite_tables(db_path: Path) -> list[str]:
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    return [row[0] for row in rows]


def _safe_read_sql(query: str, db_path: Path) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql(query, conn)


def ensure_price_metadata_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS price_metadata (
            table_name TEXT PRIMARY KEY,
            ticker TEXT NOT NULL,
            interval TEXT NOT NULL,
            period TEXT,
            row_count INTEGER NOT NULL,
            start_date TEXT,
            end_date TEXT,
            last_refreshed_utc TEXT NOT NULL
        )
        """
    )


def record_price_metadata(
    table_name: str,
    ticker: str,
    interval: str,
    period: str | None,
    df: pd.DataFrame,
    db_path: Path = MARKET_DB_PATH,
) -> None:
    ensure_data_dir()
    data = df.copy()
    if "Date" in data.columns:
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
        start_date = data["Date"].min()
        end_date = data["Date"].max()
    else:
        start_date = pd.NaT
        end_date = pd.NaT

    with _connect(db_path) as conn:
        ensure_price_metadata_table(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO price_metadata (
                table_name, ticker, interval, period, row_count, start_date, end_date, last_refreshed_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                table_name,
                ticker.upper(),
                interval,
                period,
                int(len(data)),
                None if pd.isna(start_date) else start_date.date().isoformat(),
                None if pd.isna(end_date) else end_date.date().isoformat(),
                utc_now_iso(),
            ),
        )


def inspect_market_database(db_path: Path = MARKET_DB_PATH) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame(
            columns=[
                "table_name",
                "ticker",
                "interval",
                "period",
                "row_count",
                "start_date",
                "end_date",
                "last_refreshed_utc",
                "freshness",
            ]
        )

    tables = sqlite_tables(db_path)
    with sqlite3.connect(db_path) as conn:
        ensure_price_metadata_table(conn)
        meta = pd.read_sql("SELECT * FROM price_metadata ORDER BY ticker, interval", conn)

    if meta.empty:
        rows: list[dict[str, Any]] = []
        with sqlite3.connect(db_path) as conn:
            for table in tables:
                if not table.startswith("prices_"):
                    continue
                try:
                    row_count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                    date_range = conn.execute(
                        f'SELECT MIN(Date), MAX(Date) FROM "{table}"'
                    ).fetchone()
                except Exception:
                    row_count = None
                    date_range = (None, None)
                rows.append(
                    {
                        "table_name": table,
                        "ticker": table.replace("prices_", "").upper(),
                        "interval": None,
                        "period": None,
                        "row_count": row_count,
                        "start_date": date_range[0],
                        "end_date": date_range[1],
                        "last_refreshed_utc": None,
                    }
                )
        meta = pd.DataFrame(rows)

    if not meta.empty:
        meta["freshness"] = meta["last_refreshed_utc"].apply(_freshness_label)
    return meta


def _freshness_label(value: Any) -> str:
    if not value:
        return "Unknown"
    try:
        ts = pd.to_datetime(value, utc=True)
        age_hours = (pd.Timestamp.now(tz="UTC") - ts).total_seconds() / 3600
    except Exception:
        return "Unknown"

    if age_hours <= 6:
        return "Fresh"
    if age_hours <= 24:
        return "Recent"
    if age_hours <= 24 * 7:
        return "Aging"
    return "Stale"


def is_price_data_fresh(ticker: str, interval: str, max_age_hours: float = 18.0, db_path: Path = MARKET_DB_PATH) -> bool:
    meta = inspect_market_database(db_path)
    if meta.empty:
        return False

    match = meta[
        (meta["ticker"].astype(str).str.upper() == ticker.upper())
        & (meta["interval"].astype(str) == str(interval))
    ]
    if match.empty:
        return False

    value = match.iloc[0].get("last_refreshed_utc")
    if not value:
        return False

    try:
        ts = pd.to_datetime(value, utc=True)
        age_hours = (pd.Timestamp.now(tz="UTC") - ts).total_seconds() / 3600
        return age_hours <= max_age_hours
    except Exception:
        return False


def _news_id(row: dict[str, Any]) -> str:
    raw = "|".join(
        [
            str(row.get("ticker", "")).upper(),
            str(row.get("source", "")),
            str(row.get("url", "")),
            str(row.get("title", "")),
            str(row.get("published_at", "")),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def ensure_news_cache_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS news_cache (
            id TEXT PRIMARY KEY,
            ticker TEXT NOT NULL,
            source TEXT,
            title TEXT NOT NULL,
            short_title TEXT,
            summary TEXT,
            publisher TEXT,
            published_at TEXT,
            url TEXT,
            cached_at_utc TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_news_cache_ticker ON news_cache(ticker)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_news_cache_published ON news_cache(published_at)")


def save_news_to_cache(df: pd.DataFrame, db_path: Path = NEWS_CACHE_DB_PATH) -> None:
    if df is None or df.empty:
        return

    data = df.copy()
    for col in ["ticker", "source", "title", "short_title", "summary", "publisher", "published_at", "url"]:
        if col not in data.columns:
            data[col] = ""

    data["ticker"] = data["ticker"].astype(str).str.upper()
    data["published_at"] = pd.to_datetime(data["published_at"], errors="coerce").astype(str)
    cached_at = utc_now_iso()

    rows = []
    for _, row in data.iterrows():
        record = row.to_dict()
        rows.append(
            (
                _news_id(record),
                record.get("ticker", ""),
                record.get("source", ""),
                record.get("title", ""),
                record.get("short_title", ""),
                record.get("summary", ""),
                record.get("publisher", ""),
                record.get("published_at", ""),
                record.get("url", ""),
                cached_at,
            )
        )

    with _connect(db_path) as conn:
        ensure_news_cache_table(conn)
        conn.executemany(
            """
            INSERT OR REPLACE INTO news_cache (
                id, ticker, source, title, short_title, summary, publisher, published_at, url, cached_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def load_news_from_cache(
    ticker: str,
    max_age_hours: float = 12.0,
    max_items: int = 50,
    db_path: Path = NEWS_CACHE_DB_PATH,
) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()

    ticker = ticker.upper()
    with sqlite3.connect(db_path) as conn:
        ensure_news_cache_table(conn)
        df = pd.read_sql(
            """
            SELECT ticker, title, short_title, summary, publisher, published_at, url, source, cached_at_utc
            FROM news_cache
            WHERE ticker = ?
            ORDER BY published_at DESC
            LIMIT ?
            """,
            conn,
            params=(ticker, max_items),
        )

    if df.empty:
        return df

    df["cached_at_utc"] = pd.to_datetime(df["cached_at_utc"], errors="coerce", utc=True)
    newest_cache = df["cached_at_utc"].max()
    age_hours = (pd.Timestamp.now(tz="UTC") - newest_cache).total_seconds() / 3600
    if age_hours > max_age_hours:
        return pd.DataFrame()

    df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce")
    return df.drop(columns=["cached_at_utc"])


def inspect_news_cache(db_path: Path = NEWS_CACHE_DB_PATH) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame(columns=["ticker", "source", "rows", "newest_published_at", "last_cached_at_utc"])

    with sqlite3.connect(db_path) as conn:
        ensure_news_cache_table(conn)
        return pd.read_sql(
            """
            SELECT
                ticker,
                source,
                COUNT(*) AS rows,
                MAX(published_at) AS newest_published_at,
                MAX(cached_at_utc) AS last_cached_at_utc
            FROM news_cache
            GROUP BY ticker, source
            ORDER BY ticker, source
            """,
            conn,
        )
