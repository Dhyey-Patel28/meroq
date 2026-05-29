from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
import hashlib
import json
import os
import re
import sqlite3

import pandas as pd
import requests
import yfinance as yf


# -----------------------------------------------------------------------------
# Free/local sentiment engines
# -----------------------------------------------------------------------------

SENTIMENT_ENGINE_OPTIONS = {
    "lightweight": "Lightweight financial lexicon",
    "prosus_finbert": "ProsusAI/finbert",
    "finbert_tone": "yiyanghkust/finbert-tone",
    "distilroberta_financial": "DistilRoBERTa financial news",
    "ensemble_finance": "Finance sentiment ensemble",
}

HF_MODEL_IDS = {
    "prosus_finbert": "ProsusAI/finbert",
    "finbert_tone": "yiyanghkust/finbert-tone",
    "distilroberta_financial": "mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis",
}

ENSEMBLE_ENGINES = ["prosus_finbert", "finbert_tone", "distilroberta_financial"]

NEWS_SOURCE_OPTIONS = {
    "all_configured": "All configured sources, recommended",
    "finnhub": "Finnhub company news, user key",
    "yfinance": "yfinance news, no key",
    "newsapi": "NewsAPI dev-only, user key",
    "auto_free": "Auto fallback",
}

POSITIVE_TERMS = {
    "beat", "beats", "beating", "bullish", "buy", "upgrade", "upgraded", "outperform", "growth",
    "grow", "grows", "grew", "record", "strong", "strength", "surge", "surges", "rally", "rallies",
    "gain", "gains", "profit", "profits", "profitable", "revenue", "revenues", "margin", "margins",
    "optimistic", "positive", "innovation", "launch", "launched", "expansion", "expand", "expands",
    "higher", "raised", "raise", "raises", "resilient", "rebound", "recovery", "approval", "approved",
    "partnership", "partners", "demand", "momentum", "upside", "win", "wins", "record-high", "soar", "soars",
    "breakthrough", "confidence", "accelerates", "accelerate", "boost", "boosts", "improves", "improved",
}

NEGATIVE_TERMS = {
    "miss", "misses", "missed", "bearish", "sell", "downgrade", "downgraded", "underperform",
    "decline", "declines", "declined", "drop", "drops", "dropped", "fall", "falls", "fell", "loss",
    "losses", "weak", "weakness", "lawsuit", "probe", "investigation", "risk", "risks", "warning",
    "cut", "cuts", "lower", "lowered", "slowdown", "recession", "inflation", "layoffs", "layoff",
    "recall", "volatility", "volatile", "pressure", "debt", "default", "fraud", "concern", "concerns",
    "negative", "downside", "crash", "plunge", "plunges", "slump", "slumps", "disappointing", "missed",
    "headwinds", "weakens", "weakening", "investigates", "probe", "charges", "fine", "fined", "tariff", "tariffs",
}

NEGATIONS = {"not", "no", "never", "without", "hardly", "barely", "isn't", "wasn't", "aren't", "don't", "doesn't"}
INTENSIFIERS = {"very", "much", "strongly", "significantly", "sharp", "sharply", "record"}


@dataclass
class SentimentResult:
    score: float
    label: str
    confidence: float
    positive_probability: float
    neutral_probability: float
    negative_probability: float
    engine: str
    engine_detail: str
    agreement: float | None = None


# -----------------------------------------------------------------------------
# Configuration helpers
# -----------------------------------------------------------------------------

def _load_dotenv_if_present(path: str | Path = ".env") -> None:
    """Minimal .env loader so we do not require python-dotenv."""
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _get_env_value(name: str) -> str:
    _load_dotenv_if_present()
    return os.environ.get(name, "").strip()


# -----------------------------------------------------------------------------
# News fetching: all sources are free/no-billing first
# -----------------------------------------------------------------------------

def _normalize_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc).replace(tzinfo=None)
        return pd.to_datetime(value, errors="coerce").to_pydatetime()
    except Exception:
        return None


def _shorten_title(title: str, max_len: int = 90) -> str:
    title = str(title or "").strip()
    if len(title) <= max_len:
        return title
    return title[: max_len - 3].rstrip() + "..."


def fetch_yfinance_news(ticker: str, max_items: int = 20) -> pd.DataFrame:
    """Fetch recent ticker news from yfinance. No API key, no billing."""
    ticker = ticker.strip().upper()
    if not ticker:
        return pd.DataFrame()

    try:
        news_items = yf.Ticker(ticker).news or []
    except Exception:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for item in news_items[:max_items]:
        content = item.get("content") if isinstance(item.get("content"), dict) else {}
        title = item.get("title") or content.get("title") or ""
        publisher = item.get("publisher") or content.get("provider", {}).get("displayName") or content.get("publisher") or ""
        link = item.get("link") or content.get("canonicalUrl", {}).get("url") or content.get("clickThroughUrl", {}).get("url") or ""
        published_raw = item.get("providerPublishTime") or content.get("pubDate") or content.get("displayTime")
        published_at = _normalize_timestamp(published_raw)
        summary = item.get("summary") or content.get("summary") or content.get("description") or ""

        if not title:
            continue

        rows.append(
            {
                "ticker": ticker,
                "title": title,
                "short_title": _shorten_title(title),
                "summary": summary,
                "publisher": publisher,
                "published_at": published_at,
                "url": link,
                "source": "yfinance",
            }
        )

    return pd.DataFrame(rows)


def fetch_finnhub_news(ticker: str, max_items: int = 20, days_back: int = 14) -> pd.DataFrame:
    """Fetch recent company news from Finnhub's free API when FINNHUB_API_KEY is configured."""
    api_key = _get_env_value("FINNHUB_API_KEY")
    if not api_key:
        return pd.DataFrame()

    ticker = ticker.strip().upper()
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days_back)
    url = "https://finnhub.io/api/v1/company-news"
    params = {"symbol": ticker, "from": start_date.isoformat(), "to": end_date.isoformat(), "token": api_key}

    try:
        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        items = response.json() or []
    except Exception:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for item in items[:max_items]:
        title = item.get("headline") or ""
        if not title:
            continue
        rows.append(
            {
                "ticker": ticker,
                "title": title,
                "short_title": _shorten_title(title),
                "summary": item.get("summary") or "",
                "publisher": item.get("source") or "Finnhub",
                "published_at": _normalize_timestamp(item.get("datetime")),
                "url": item.get("url") or "",
                "source": "finnhub",
            }
        )
    return pd.DataFrame(rows)


def fetch_newsapi_news(ticker: str, max_items: int = 20, days_back: int = 14) -> pd.DataFrame:
    """Fetch recent news from NewsAPI Developer API when NEWSAPI_API_KEY is configured."""
    api_key = _get_env_value("NEWSAPI_API_KEY")
    if not api_key:
        return pd.DataFrame()

    ticker = ticker.strip().upper()
    from_date = (datetime.utcnow().date() - timedelta(days=days_back)).isoformat()
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": ticker,
        "from": from_date,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": min(max_items, 100),
        "apiKey": api_key,
    }

    try:
        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        payload = response.json() or {}
        items = payload.get("articles") or []
    except Exception:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for item in items[:max_items]:
        title = item.get("title") or ""
        if not title:
            continue
        source = item.get("source") or {}
        rows.append(
            {
                "ticker": ticker,
                "title": title,
                "short_title": _shorten_title(title),
                "summary": item.get("description") or "",
                "publisher": source.get("name") or "NewsAPI",
                "published_at": _normalize_timestamp(item.get("publishedAt")),
                "url": item.get("url") or "",
                "source": "newsapi",
            }
        )
    return pd.DataFrame(rows)



# -----------------------------------------------------------------------------
# News cache, aggregation, and source selection
# -----------------------------------------------------------------------------

NEWS_CACHE_DB = Path("data/news_cache.sqlite")


def _safe_json_loads(value: str, default: Any):
    try:
        return json.loads(value)
    except Exception:
        return default


def _cache_signature(ticker: str, source: str, max_items: int, days_back: int) -> str:
    """Cache key that never includes API key values."""
    key_presence = {
        "finnhub": bool(_get_env_value("FINNHUB_API_KEY")),
        "newsapi": bool(_get_env_value("NEWSAPI_API_KEY")),
    }
    payload = {
        "ticker": ticker.upper().strip(),
        "source": source,
        "max_items": int(max_items),
        "days_back": int(days_back),
        "key_presence": key_presence,
        "version": "news-cache-v2",
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _ensure_news_cache() -> None:
    NEWS_CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(NEWS_CACHE_DB) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS news_cache (
                cache_key TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                records_json TEXT NOT NULL,
                meta_json TEXT NOT NULL
            )
            """
        )


def _read_news_cache(cache_key: str, ttl_minutes: int) -> tuple[pd.DataFrame, dict[str, Any]] | None:
    if ttl_minutes <= 0 or not NEWS_CACHE_DB.exists():
        return None
    try:
        with sqlite3.connect(NEWS_CACHE_DB) as conn:
            row = conn.execute(
                "SELECT created_at, records_json, meta_json FROM news_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
    except Exception:
        return None

    if not row:
        return None
    created_at = pd.to_datetime(row[0], errors="coerce")
    if pd.isna(created_at):
        return None
    age_minutes = (datetime.utcnow() - created_at.to_pydatetime()).total_seconds() / 60
    if age_minutes > ttl_minutes:
        return None

    records = _safe_json_loads(row[1], [])
    meta = _safe_json_loads(row[2], {})
    df = pd.DataFrame(records)
    if "published_at" in df.columns:
        df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce")
    meta["cache_hit"] = True
    meta["cache_age_minutes"] = round(age_minutes, 1)
    return df, meta


def _write_news_cache(cache_key: str, ticker: str, source: str, df: pd.DataFrame, meta: dict[str, Any]) -> None:
    try:
        _ensure_news_cache()
        cache_meta = dict(meta)
        cache_meta["cache_hit"] = False
        records_json = df.to_json(orient="records", date_format="iso") if df is not None else "[]"
        with sqlite3.connect(NEWS_CACHE_DB) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO news_cache(cache_key, ticker, source, created_at, records_json, meta_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    cache_key,
                    ticker.upper().strip(),
                    source,
                    datetime.utcnow().isoformat(),
                    records_json,
                    json.dumps(cache_meta, default=str),
                ),
            )
    except Exception:
        # Cache failures should never break the app.
        return


def _news_dedupe_key(row: pd.Series) -> str:
    url = str(row.get("url", "") or "").strip().lower()
    if url:
        return "url:" + url
    title = str(row.get("title", "") or "").lower()
    title = re.sub(r"[^a-z0-9]+", " ", title).strip()
    return "title:" + title[:140]


def _combine_news_frames(frames: list[pd.DataFrame], max_items: int) -> pd.DataFrame:
    valid = [df.copy() for df in frames if df is not None and not df.empty]
    if not valid:
        return pd.DataFrame()
    combined = pd.concat(valid, ignore_index=True)
    if combined.empty:
        return combined
    combined["_dedupe_key"] = combined.apply(_news_dedupe_key, axis=1)
    combined = combined.drop_duplicates(subset=["_dedupe_key"], keep="first").drop(columns=["_dedupe_key"])
    if "published_at" in combined.columns:
        combined["published_at"] = pd.to_datetime(combined["published_at"], errors="coerce")
        combined = combined.sort_values("published_at", ascending=False, na_position="last")
    return combined.head(max_items).reset_index(drop=True)


def _source_counts(df: pd.DataFrame) -> dict[str, int]:
    if df is None or df.empty or "source" not in df.columns:
        return {}
    return {str(k): int(v) for k, v in df["source"].fillna("unknown").value_counts().to_dict().items()}


def _finalize_news_result(
    ticker: str,
    source: str,
    max_items: int,
    days_back: int,
    df: pd.DataFrame,
    meta: dict[str, Any],
    cache_key: str,
    use_cache: bool,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if df is None:
        df = pd.DataFrame()
    if "published_at" in df.columns:
        df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce")
    df = df.head(max_items).reset_index(drop=True)
    meta["headline_count"] = int(len(df))
    meta["source_counts"] = _source_counts(df)
    meta["days_back"] = int(days_back)
    meta.setdefault("cache_hit", False)
    if use_cache and not df.empty:
        _write_news_cache(cache_key, ticker, source, df, meta)
    return df, meta


def fetch_news_for_ticker(
    ticker: str,
    source: str = "all_configured",
    max_items: int = 20,
    days_back: int = 14,
    use_cache: bool = True,
    cache_ttl_minutes: int = 60,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fetch news using local/no-key sources plus optional user-provided API keys.

    No API key values are stored in the repo. Optional keys are read from `.env`.
    `newsapi` is labeled development-only because NewsAPI's free plan is not intended
    for hosted/staging/production usage.
    """
    source = source or "all_configured"
    ticker = ticker.strip().upper()
    max_items = int(max_items)
    days_back = int(days_back)
    cache_key = _cache_signature(ticker, source, max_items, days_back)

    meta: dict[str, Any] = {
        "requested_source": source,
        "source_used": None,
        "api_key_required": source in {"finnhub", "newsapi"},
        "finnhub_key_found": bool(_get_env_value("FINNHUB_API_KEY")),
        "newsapi_key_found": bool(_get_env_value("NEWSAPI_API_KEY")),
        "fallback_used": False,
        "cache_hit": False,
        "notes": [],
    }

    cached = _read_news_cache(cache_key, cache_ttl_minutes) if use_cache else None
    if cached is not None:
        df, cached_meta = cached
        cached_meta.setdefault("notes", [])
        cached_meta["notes"].append("Loaded from local news cache.")
        return df, cached_meta

    if source == "yfinance":
        df = fetch_yfinance_news(ticker, max_items=max_items)
        meta["source_used"] = "yfinance"
        return _finalize_news_result(ticker, source, max_items, days_back, df, meta, cache_key, use_cache)

    if source == "finnhub":
        df = fetch_finnhub_news(ticker, max_items=max_items, days_back=days_back)
        meta["source_used"] = "finnhub" if not df.empty else None
        if df.empty:
            meta["notes"].append("Finnhub returned no rows or FINNHUB_API_KEY is missing; falling back to yfinance.")
            df = fetch_yfinance_news(ticker, max_items=max_items)
            meta["source_used"] = "yfinance"
            meta["fallback_used"] = True
        return _finalize_news_result(ticker, source, max_items, days_back, df, meta, cache_key, use_cache)

    if source == "newsapi":
        df = fetch_newsapi_news(ticker, max_items=max_items, days_back=days_back)
        meta["source_used"] = "newsapi" if not df.empty else None
        meta["notes"].append("NewsAPI free Developer usage is intended for local development/testing only.")
        if df.empty:
            meta["notes"].append("NewsAPI returned no rows or NEWSAPI_API_KEY is missing; falling back to yfinance.")
            df = fetch_yfinance_news(ticker, max_items=max_items)
            meta["source_used"] = "yfinance"
            meta["fallback_used"] = True
        return _finalize_news_result(ticker, source, max_items, days_back, df, meta, cache_key, use_cache)

    if source == "all_configured":
        frames: list[pd.DataFrame] = []
        yf_df = fetch_yfinance_news(ticker, max_items=max_items)
        if not yf_df.empty:
            frames.append(yf_df)
        if meta["finnhub_key_found"]:
            fh_df = fetch_finnhub_news(ticker, max_items=max_items, days_back=days_back)
            if not fh_df.empty:
                frames.append(fh_df)
        if meta["newsapi_key_found"]:
            na_df = fetch_newsapi_news(ticker, max_items=max_items, days_back=days_back)
            if not na_df.empty:
                frames.append(na_df)
                meta["notes"].append("NewsAPI results are included for local development/testing only.")
        df = _combine_news_frames(frames, max_items=max_items)
        meta["source_used"] = "mixed" if len(_source_counts(df)) > 1 else (next(iter(_source_counts(df)), "none"))
        if df.empty:
            meta["notes"].append("No configured source returned headlines.")
        return _finalize_news_result(ticker, source, max_items, days_back, df, meta, cache_key, use_cache)

    # auto_free: no-key first, then optional configured APIs as fallback only.
    yf_df = fetch_yfinance_news(ticker, max_items=max_items)
    if not yf_df.empty:
        meta["source_used"] = "yfinance"
        return _finalize_news_result(ticker, source, max_items, days_back, yf_df, meta, cache_key, use_cache)

    finnhub_df = fetch_finnhub_news(ticker, max_items=max_items, days_back=days_back)
    if not finnhub_df.empty:
        meta["source_used"] = "finnhub"
        meta["fallback_used"] = True
        return _finalize_news_result(ticker, source, max_items, days_back, finnhub_df, meta, cache_key, use_cache)

    newsapi_df = fetch_newsapi_news(ticker, max_items=max_items, days_back=days_back)
    if not newsapi_df.empty:
        meta["source_used"] = "newsapi"
        meta["fallback_used"] = True
        meta["notes"].append("NewsAPI fallback is intended for local development/testing only.")
        return _finalize_news_result(ticker, source, max_items, days_back, newsapi_df, meta, cache_key, use_cache)

    meta["source_used"] = "none"
    meta["notes"].append("No news source returned headlines.")
    return _finalize_news_result(ticker, source, max_items, days_back, pd.DataFrame(), meta, cache_key, use_cache)


# -----------------------------------------------------------------------------
# Sentiment scoring
# -----------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z\-']+", str(text).lower())


def score_text_lightweight(text: str) -> SentimentResult:
    """Small deterministic finance lexicon fallback."""
    tokens = _tokenize(text)
    pos_score = 0.0
    neg_score = 0.0

    for i, token in enumerate(tokens):
        weight = 1.0
        if i > 0 and tokens[i - 1] in INTENSIFIERS:
            weight += 0.4
        if i > 0 and tokens[i - 1] in NEGATIONS:
            weight *= -1

        if token in POSITIVE_TERMS:
            if weight >= 0:
                pos_score += weight
            else:
                neg_score += abs(weight)
        elif token in NEGATIVE_TERMS:
            if weight >= 0:
                neg_score += weight
            else:
                pos_score += abs(weight)

    raw = pos_score - neg_score
    normalized = max(-1.0, min(1.0, raw / 4.0))

    if normalized >= 0.12:
        label = "Positive"
    elif normalized <= -0.12:
        label = "Negative"
    else:
        label = "Neutral"

    confidence = min(0.95, 0.45 + abs(normalized) * 0.5)
    pos_prob = max(0.0, normalized)
    neg_prob = max(0.0, -normalized)
    neutral_prob = max(0.0, 1.0 - pos_prob - neg_prob)
    total = pos_prob + neutral_prob + neg_prob or 1.0

    return SentimentResult(
        score=float(normalized),
        label=label,
        confidence=float(confidence),
        positive_probability=float(pos_prob / total),
        neutral_probability=float(neutral_prob / total),
        negative_probability=float(neg_prob / total),
        engine="lightweight",
        engine_detail="Lightweight financial lexicon",
    )


@lru_cache(maxsize=4)
def _load_hf_pipeline(model_id: str):
    """Load a Hugging Face text-classification pipeline lazily and cache it locally."""
    try:
        from transformers import pipeline
    except Exception as exc:
        raise RuntimeError("transformers is not installed. Run: python -m pip install -r requirements-nlp.txt") from exc

    try:
        return pipeline("text-classification", model=model_id, tokenizer=model_id, top_k=None, device=-1)
    except Exception as exc:
        raise RuntimeError(f"Could not load Hugging Face model {model_id}: {exc}") from exc


def _normalize_model_scores(raw_scores: list[dict[str, Any]]) -> dict[str, float]:
    probs = {"positive": 0.0, "neutral": 0.0, "negative": 0.0}
    for item in raw_scores:
        raw_label = str(item.get("label", "")).lower().strip()
        score = float(item.get("score", 0.0) or 0.0)
        if "pos" in raw_label or raw_label in {"label_2", "2"}:
            probs["positive"] += score
        elif "neg" in raw_label or raw_label in {"label_0", "0"}:
            probs["negative"] += score
        elif "neu" in raw_label or raw_label in {"label_1", "1"}:
            probs["neutral"] += score
        else:
            # Unknown labels default to neutral rather than forcing a direction.
            probs["neutral"] += score

    total = sum(probs.values()) or 1.0
    return {k: float(v / total) for k, v in probs.items()}


def score_text_hf(text: str, engine: str) -> SentimentResult:
    """Score one text with a selected Hugging Face financial sentiment model."""
    if engine not in HF_MODEL_IDS:
        raise ValueError(f"Unknown Hugging Face sentiment engine: {engine}")

    model_id = HF_MODEL_IDS[engine]
    classifier = _load_hf_pipeline(model_id)
    text = str(text or "")[:512]
    raw = classifier(text)
    if raw and isinstance(raw[0], list):
        raw_scores = raw[0]
    else:
        raw_scores = raw

    probs = _normalize_model_scores(raw_scores)
    label_key = max(probs, key=probs.get)
    label = label_key.capitalize()
    score = probs["positive"] - probs["negative"]
    confidence = probs[label_key]

    return SentimentResult(
        score=float(score),
        label=label,
        confidence=float(confidence),
        positive_probability=float(probs["positive"]),
        neutral_probability=float(probs["neutral"]),
        negative_probability=float(probs["negative"]),
        engine=engine,
        engine_detail=SENTIMENT_ENGINE_OPTIONS.get(engine, model_id),
    )


def score_text_ensemble(text: str) -> SentimentResult:
    """Average the available strong finance models; fall back safely when needed."""
    model_results: list[SentimentResult] = []
    failure_notes: list[str] = []

    for engine in ENSEMBLE_ENGINES:
        try:
            model_results.append(score_text_hf(text, engine))
        except Exception as exc:
            failure_notes.append(f"{engine}: {exc}")

    if not model_results:
        fallback = score_text_lightweight(text)
        fallback.engine = "ensemble_finance"
        fallback.engine_detail = "Ensemble unavailable; used lightweight fallback"
        fallback.agreement = None
        return fallback

    pos = sum(r.positive_probability for r in model_results) / len(model_results)
    neu = sum(r.neutral_probability for r in model_results) / len(model_results)
    neg = sum(r.negative_probability for r in model_results) / len(model_results)
    probs = {"Positive": pos, "Neutral": neu, "Negative": neg}
    label = max(probs, key=probs.get)
    score = pos - neg
    confidence = probs[label]
    votes = [r.label for r in model_results]
    agreement = votes.count(label) / len(votes)

    detail = ", ".join(SENTIMENT_ENGINE_OPTIONS.get(r.engine, r.engine) for r in model_results)
    if failure_notes:
        detail += f"; skipped {len(failure_notes)} unavailable model(s)"

    return SentimentResult(
        score=float(score),
        label=label,
        confidence=float(confidence),
        positive_probability=float(pos),
        neutral_probability=float(neu),
        negative_probability=float(neg),
        engine="ensemble_finance",
        engine_detail=detail,
        agreement=float(agreement),
    )


def score_text(text: str, engine: str = "lightweight") -> SentimentResult:
    """Score text with the selected engine and safely fall back to lightweight mode."""
    engine = engine or "lightweight"
    if engine == "lightweight":
        return score_text_lightweight(text)
    if engine == "ensemble_finance":
        return score_text_ensemble(text)
    if engine in HF_MODEL_IDS:
        try:
            return score_text_hf(text, engine)
        except Exception as exc:
            fallback = score_text_lightweight(text)
            fallback.engine = engine
            fallback.engine_detail = f"{SENTIMENT_ENGINE_OPTIONS.get(engine, engine)} unavailable; used lightweight fallback: {exc}"
            return fallback
    return score_text_lightweight(text)


def analyze_news_sentiment(news_df: pd.DataFrame, engine: str = "lightweight") -> pd.DataFrame:
    """Analyze a DataFrame of news rows and return headline-level sentiment."""
    if news_df is None or news_df.empty:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for _, row in news_df.iterrows():
        title = str(row.get("title", "") or "")
        summary = str(row.get("summary", "") or "")
        text = f"{title}. {summary}".strip()
        result = score_text(text, engine=engine)

        enriched = row.to_dict()
        enriched.update(
            {
                "sentiment_label": result.label,
                "sentiment_score": result.score,
                "confidence": result.confidence,
                "positive_probability": result.positive_probability,
                "neutral_probability": result.neutral_probability,
                "negative_probability": result.negative_probability,
                "sentiment_engine": result.engine,
                "sentiment_engine_detail": result.engine_detail,
                "model_agreement": result.agreement,
            }
        )
        rows.append(enriched)

    sentiment_df = pd.DataFrame(rows)
    if "published_at" in sentiment_df.columns:
        sentiment_df["published_at"] = pd.to_datetime(sentiment_df["published_at"], errors="coerce")
    return sentiment_df


def summarize_sentiment(sentiment_df: pd.DataFrame) -> dict[str, Any]:
    """Aggregate headline sentiment into a dashboard summary."""
    if sentiment_df is None or sentiment_df.empty or "sentiment_label" not in sentiment_df.columns:
        return {
            "available": False,
            "headline_count": 0,
            "overall_label": "No news",
            "average_score": 0.0,
            "positive_count": 0,
            "neutral_count": 0,
            "negative_count": 0,
            "confidence": 0.0,
            "agreement": None,
            "engine": "none",
            "source_used": "none",
        }

    count = len(sentiment_df)
    labels = sentiment_df["sentiment_label"].astype(str)
    positive_count = int((labels == "Positive").sum())
    neutral_count = int((labels == "Neutral").sum())
    negative_count = int((labels == "Negative").sum())
    average_score = float(pd.to_numeric(sentiment_df["sentiment_score"], errors="coerce").fillna(0.0).mean())
    confidence = float(pd.to_numeric(sentiment_df["confidence"], errors="coerce").fillna(0.0).mean())

    agreement_value = None
    if "model_agreement" in sentiment_df.columns:
        agreements = pd.to_numeric(sentiment_df["model_agreement"], errors="coerce").dropna()
        if not agreements.empty:
            agreement_value = float(agreements.mean())

    if average_score >= 0.12:
        overall_label = "Positive"
    elif average_score <= -0.12:
        overall_label = "Negative"
    else:
        overall_label = "Neutral"

    engine = "mixed"
    if "sentiment_engine" in sentiment_df.columns and not sentiment_df["sentiment_engine"].dropna().empty:
        engines = sentiment_df["sentiment_engine"].dropna().astype(str).unique().tolist()
        engine = engines[0] if len(engines) == 1 else "mixed"

    source_used = "mixed"
    if "source" in sentiment_df.columns and not sentiment_df["source"].dropna().empty:
        sources = sentiment_df["source"].dropna().astype(str).unique().tolist()
        source_used = sources[0] if len(sources) == 1 else "mixed"

    return {
        "available": True,
        "headline_count": count,
        "average_score": average_score,
        "positive_count": positive_count,
        "neutral_count": neutral_count,
        "negative_count": negative_count,
        "positive_ratio": positive_count / count if count else 0.0,
        "negative_ratio": negative_count / count if count else 0.0,
        "overall_label": overall_label,
        "confidence": confidence,
        "agreement": agreement_value,
        "engine": engine,
        "source_used": source_used,
    }


def sentiment_context_sentence(summary: dict[str, Any]) -> str:
    """Return a human-readable interpretation for the UI."""
    if not summary.get("available"):
        return "No recent headlines were returned for this ticker. Meroq can still run price, model, and risk analysis."

    label = summary.get("overall_label", "Neutral").lower()
    agreement = summary.get("agreement")
    agreement_text = f" Average model agreement is {agreement:.1%}." if agreement is not None else ""
    return (
        f"Recent headline sentiment is **{label}** across {summary['headline_count']} headlines. "
        f"Average sentiment score is {summary['average_score']:+.2f}, with "
        f"{summary['positive_count']} positive, {summary['neutral_count']} neutral, and "
        f"{summary['negative_count']} negative headlines.{agreement_text}"
    )


def sentiment_engine_availability() -> pd.DataFrame:
    """Return availability hints for the optional NLP stack."""
    rows = []
    try:
        import transformers  # noqa: F401
        transformers_ok = True
    except Exception:
        transformers_ok = False

    rows.append({"engine": "lightweight", "label": SENTIMENT_ENGINE_OPTIONS["lightweight"], "available": True, "notes": "Always available"})
    for engine, model_id in HF_MODEL_IDS.items():
        rows.append(
            {
                "engine": engine,
                "label": SENTIMENT_ENGINE_OPTIONS[engine],
                "available": transformers_ok,
                "notes": "Requires requirements-nlp.txt; downloads model on first use" if transformers_ok else "Install with: python -m pip install -r requirements-nlp.txt",
                "model_id": model_id,
            }
        )
    rows.append(
        {
            "engine": "ensemble_finance",
            "label": SENTIMENT_ENGINE_OPTIONS["ensemble_finance"],
            "available": transformers_ok,
            "notes": "Uses available Hugging Face finance models; falls back safely if none load",
        }
    )
    return pd.DataFrame(rows)
