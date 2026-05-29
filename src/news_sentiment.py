from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
import os
import re

import pandas as pd
import requests
import yfinance as yf

from src.storage import load_news_from_cache, save_news_to_cache


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
    "yfinance": "yfinance news, no API key",
    "finnhub": "Finnhub free API, optional key",
    "newsapi": "NewsAPI developer API, optional key",
    "auto_free": "Auto free fallback",
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


def _deduplicate_news(df: pd.DataFrame, max_items: int) -> pd.DataFrame:
    """Deduplicate news by URL/title while preserving source coverage."""
    if df is None or df.empty:
        return pd.DataFrame()

    data = df.copy()
    for col in ["ticker", "title", "short_title", "summary", "publisher", "published_at", "url", "source"]:
        if col not in data.columns:
            data[col] = ""

    data["title_key"] = data["title"].astype(str).str.lower().str.replace(r"\\s+", " ", regex=True).str.strip()
    data["url_key"] = data["url"].astype(str).str.lower().str.strip()
    data["dedupe_key"] = data["url_key"].where(data["url_key"] != "", data["title_key"])
    data["published_at"] = pd.to_datetime(data["published_at"], errors="coerce")
    data = data.sort_values(["published_at", "source"], ascending=[False, True])
    data = data.drop_duplicates(subset=["dedupe_key"], keep="first")
    data = data.drop(columns=["title_key", "url_key", "dedupe_key"])
    return data.head(max_items).reset_index(drop=True)


def _fetch_all_configured_sources(ticker: str, max_items: int = 30, days_back: int = 14) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Fetch yfinance plus any configured optional free developer sources."""
    frames: list[pd.DataFrame] = []
    sources_used: list[str] = []
    notes: list[str] = []

    yf_df = fetch_yfinance_news(ticker, max_items=max_items)
    if not yf_df.empty:
        frames.append(yf_df)
        sources_used.append("yfinance")
    else:
        notes.append("yfinance returned no headlines.")

    if _get_env_value("FINNHUB_API_KEY"):
        finnhub_df = fetch_finnhub_news(ticker, max_items=max_items, days_back=days_back)
        if not finnhub_df.empty:
            frames.append(finnhub_df)
            sources_used.append("finnhub")
        else:
            notes.append("Finnhub key found but returned no headlines for this ticker/window.")
    else:
        notes.append("FINNHUB_API_KEY not configured; skipped Finnhub.")

    if _get_env_value("NEWSAPI_API_KEY"):
        newsapi_df = fetch_newsapi_news(ticker, max_items=max_items, days_back=days_back)
        if not newsapi_df.empty:
            frames.append(newsapi_df)
            sources_used.append("newsapi")
        else:
            notes.append("NewsAPI key found but returned no headlines for this ticker/window.")
    else:
        notes.append("NEWSAPI_API_KEY not configured; skipped NewsAPI.")

    if not frames:
        return pd.DataFrame(), sources_used, notes

    combined = _deduplicate_news(pd.concat(frames, ignore_index=True), max_items=max_items)
    return combined, sources_used, notes


def fetch_news_for_ticker(
    ticker: str,
    source: str = "yfinance",
    max_items: int = 20,
    days_back: int = 14,
    use_cache: bool = True,
    force_refresh: bool = False,
    cache_max_age_hours: float = 12.0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fetch news using a selected free-safe source strategy with local caching."""
    source = source or "yfinance"
    ticker = ticker.strip().upper()
    meta: dict[str, Any] = {
        "requested_source": source,
        "source_used": None,
        "sources_used": [],
        "api_key_required": source in {"finnhub", "newsapi"},
        "api_key_found": False,
        "fallback_used": False,
        "cache_used": False,
        "notes": [],
    }

    if use_cache and not force_refresh:
        cached = load_news_from_cache(ticker=ticker, max_age_hours=cache_max_age_hours, max_items=max_items)
        if not cached.empty:
            meta["source_used"] = "local_cache"
            meta["sources_used"] = sorted(cached["source"].dropna().astype(str).unique().tolist())
            meta["cache_used"] = True
            meta["notes"].append(f"Used local news cache younger than {cache_max_age_hours:g} hours.")
            return cached, meta

    if source == "all_configured":
        df, sources_used, notes = _fetch_all_configured_sources(ticker, max_items=max_items, days_back=days_back)
        meta["source_used"] = "all_configured" if not df.empty else "none"
        meta["sources_used"] = sources_used
        meta["api_key_found"] = bool(_get_env_value("FINNHUB_API_KEY") or _get_env_value("NEWSAPI_API_KEY"))
        meta["notes"].extend(notes)
        if not df.empty:
            save_news_to_cache(df)
        return df, meta

    if source == "yfinance":
        df = fetch_yfinance_news(ticker, max_items=max_items)
        meta["source_used"] = "yfinance"
        meta["sources_used"] = ["yfinance"] if not df.empty else []
        if not df.empty:
            save_news_to_cache(df)
        return df, meta

    if source == "finnhub":
        meta["api_key_found"] = bool(_get_env_value("FINNHUB_API_KEY"))
        df = fetch_finnhub_news(ticker, max_items=max_items, days_back=days_back)
        meta["source_used"] = "finnhub" if not df.empty else None
        meta["sources_used"] = ["finnhub"] if not df.empty else []
        if df.empty:
            meta["notes"].append("Finnhub returned no rows or FINNHUB_API_KEY is missing; falling back to yfinance.")
            fallback = fetch_yfinance_news(ticker, max_items=max_items)
            meta["source_used"] = "yfinance"
            meta["sources_used"] = ["yfinance"] if not fallback.empty else []
            meta["fallback_used"] = True
            if not fallback.empty:
                save_news_to_cache(fallback)
            return fallback, meta
        save_news_to_cache(df)
        return df, meta

    if source == "newsapi":
        meta["api_key_found"] = bool(_get_env_value("NEWSAPI_API_KEY"))
        df = fetch_newsapi_news(ticker, max_items=max_items, days_back=days_back)
        meta["source_used"] = "newsapi" if not df.empty else None
        meta["sources_used"] = ["newsapi"] if not df.empty else []
        if df.empty:
            meta["notes"].append("NewsAPI returned no rows or NEWSAPI_API_KEY is missing; falling back to yfinance.")
            fallback = fetch_yfinance_news(ticker, max_items=max_items)
            meta["source_used"] = "yfinance"
            meta["sources_used"] = ["yfinance"] if not fallback.empty else []
            meta["fallback_used"] = True
            if not fallback.empty:
                save_news_to_cache(fallback)
            return fallback, meta
        save_news_to_cache(df)
        return df, meta

    # auto_free: try no-key first, then optional configured free APIs.
    yf_df = fetch_yfinance_news(ticker, max_items=max_items)
    if not yf_df.empty:
        meta["source_used"] = "yfinance"
        meta["sources_used"] = ["yfinance"]
        save_news_to_cache(yf_df)
        return yf_df, meta

    finnhub_df = fetch_finnhub_news(ticker, max_items=max_items, days_back=days_back)
    if not finnhub_df.empty:
        meta["source_used"] = "finnhub"
        meta["sources_used"] = ["finnhub"]
        meta["api_key_found"] = True
        meta["fallback_used"] = True
        save_news_to_cache(finnhub_df)
        return finnhub_df, meta

    newsapi_df = fetch_newsapi_news(ticker, max_items=max_items, days_back=days_back)
    if not newsapi_df.empty:
        meta["source_used"] = "newsapi"
        meta["sources_used"] = ["newsapi"]
        meta["api_key_found"] = True
        meta["fallback_used"] = True
        save_news_to_cache(newsapi_df)
        return newsapi_df, meta

    meta["source_used"] = "none"
    meta["notes"].append("No news source returned headlines.")
    return pd.DataFrame(), meta


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
        raise RuntimeError("transformers is not installed. Run: python -m pip install -r requirements.txt") from exc

    try:
        return pipeline("text-classification", model=model_id, tokenizer=model_id, return_all_scores=True, device=-1)
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
                "notes": "Requires requirements.txt; downloads model on first use" if transformers_ok else "Install with: python -m pip install -r requirements.txt",
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
