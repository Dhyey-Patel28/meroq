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
try:
    import yfinance as yf
except Exception:  # pragma: no cover - optional dependency guard for lightweight evaluation/tests
    yf = None

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

TARGET_NEGATIVE_PATTERNS = [
    ("risk-language", r"\b(risky|risk|risks|avoid|caution|cautious|warning|warns|concern|concerns|bearish|underperform|sell)\b"),
    ("negative-price-action", r"\b(falls|fell|falling|drops|dropped|declines|slumps|plunges|slides|sinks|tumbles)\b"),
    ("negative-fundamental-event", r"\b(miss|misses|missed|cuts|cut|lowers|lowered|downgrade|downgraded|lawsuit|probe|investigation|recall|fraud|loss|losses|weak|weakness|headwinds)\b"),
    ("buy-alternative-framing", r"\b(stock|stocks|name|company)\s+to\s+buy\s+instead\b|\bbuy\s+instead\b|\binstead\s+of\b"),
]

TARGET_POSITIVE_PATTERNS = [
    ("positive-analyst-action", r"\b(upgrade|upgraded|raises?\s+(?:price\s+target|rating)|outperform|buy\s+rating|initiates?\s+at\s+buy)\b"),
    ("positive-fundamental-event", r"\b(beats?|beat|raises?\s+guidance|record\s+(?:revenue|profit|sales)|strong\s+(?:earnings|quarter|demand)|profit\s+jumps?|revenue\s+grows?)\b"),
    ("positive-price-action", r"\b(rallies|rally|surges|jumps|gains|soars|breaks?\s+out|hits?\s+record)\b"),
]

CAUTIONARY_LABEL = "Cautionary"
IRRELEVANT_LABEL = "Irrelevant"
UNCERTAIN_LABEL = "Uncertain"


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




# -----------------------------------------------------------------------------
# Company identity + relevance helpers
# -----------------------------------------------------------------------------

COMPANY_SUFFIX_PATTERN = re.compile(
    r"\b(incorporated|inc\.?|corp\.?|corporation|co\.?|company|ltd\.?|limited|plc|holdings?|group|class\s+[a-z]|common\s+stock|ordinary\s+shares)\b",
    flags=re.IGNORECASE,
)

# Tickers that are common English words or too ambiguous for broad news search.
# For these, Meroq avoids using the raw ticker as the primary NewsAPI query.
AMBIGUOUS_TICKERS = {
    "A", "AA", "AI", "ALL", "ARE", "ARM", "BE", "BIG", "BOX", "BY", "CAN", "CAR", "CAT", "CASH",
    "COIN", "COOL", "COST", "DASH", "DD", "DNA", "DOC", "EYE", "F", "FAST", "FIVE", "FOR", "GO",
    "GOOD", "HAS", "HE", "HIM", "HOOD", "JOB", "KEY", "LIFE", "LOVE", "MAN", "NOW", "ON", "OPEN",
    "PLAY", "REAL", "RUN", "SAVE", "SNAP", "SO", "T", "TEAM", "TOY", "TRUE", "U", "UP", "VIEW", "W", "YOU",
}

FINANCE_CONTEXT_TERMS = {
    "stock", "stocks", "share", "shares", "market", "markets", "investor", "investors", "analyst", "analysts",
    "earnings", "revenue", "profit", "profits", "sales", "guidance", "price target", "rating", "upgrade",
    "downgrade", "nasdaq", "nyse", "quarter", "fiscal", "dividend", "buyback", "sec", "filing",
}

# Small manual fallback map for ambiguous tickers when yfinance profile lookup fails.
# This is not intended to replace live metadata; it only protects common-word tickers.
COMPANY_NAME_OVERRIDES = {
    "PLAY": "Dave & Buster's Entertainment, Inc.",
}


def _clean_company_name(value: str) -> str:
    """Normalize a company name for query generation and matching."""
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.replace("&", " and ")
    text = text.replace("’", "'")
    text = re.sub(r"\([^)]*\)", " ", text)
    text = COMPANY_SUFFIX_PATTERN.sub(" ", text)
    text = re.sub(r"[^A-Za-z0-9' ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _compact_company_phrase(value: str) -> str:
    """Return a lower-case alphanumeric phrase used for fuzzy containment."""
    cleaned = _clean_company_name(value).lower()
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _company_aliases_from_names(ticker: str, *names: str) -> list[str]:
    """Build company aliases from yfinance profile names."""
    aliases: list[str] = []
    for name in names:
        raw = str(name or "").strip()
        cleaned = _clean_company_name(raw)
        candidates = [raw, cleaned]

        # Finance names often include "Entertainment", "Holdings", etc. Keep a shorter
        # leading phrase as another alias so Dave & Buster's Entertainment matches Dave & Buster.
        words = cleaned.split()
        if len(words) >= 2:
            candidates.append(" ".join(words[:2]))
        if len(words) >= 3:
            candidates.append(" ".join(words[:3]))

        # Handle apostrophe/ampersand variations that are common in news feeds.
        expanded: list[str] = []
        for candidate in candidates:
            c = str(candidate or "").strip()
            if not c:
                continue
            expanded.extend(
                {
                    c,
                    c.replace("&", "and"),
                    c.replace(" and ", " & "),
                    c.replace("'", ""),
                    c.replace("’", ""),
                }
            )
        for candidate in expanded:
            candidate = re.sub(r"\s+", " ", candidate).strip(" ,.-")
            if len(candidate) >= 3 and candidate.lower() not in {"inc", "corp", "company", "group", "holdings"}:
                aliases.append(candidate)

    # For ambiguous tickers like PLAY, do not let the ticker dominate broad search.
    ticker = str(ticker or "").upper().strip()
    if ticker and ticker not in AMBIGUOUS_TICKERS and len(ticker) > 2:
        aliases.append(ticker)

    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for alias in aliases:
        key = _compact_company_phrase(alias)
        if key and key not in seen:
            seen.add(key)
            unique.append(alias)
    return unique[:8]


@lru_cache(maxsize=256)
def resolve_company_profile(ticker: str) -> dict[str, Any]:
    """Resolve a ticker into company identity metadata for safer news search."""
    ticker = str(ticker or "").upper().strip()
    long_name = ""
    short_name = ""
    exchange = ""
    quote_type = ""
    sector = ""
    industry = ""

    if ticker and yf is not None:
        try:
            info = yf.Ticker(ticker).get_info() or {}
            long_name = str(info.get("longName") or "").strip()
            short_name = str(info.get("shortName") or "").strip()
            exchange = str(info.get("exchange") or info.get("fullExchangeName") or "").strip()
            quote_type = str(info.get("quoteType") or "").strip()
            sector = str(info.get("sector") or "").strip()
            industry = str(info.get("industry") or "").strip()
        except Exception:
            # yfinance profile lookup may fail even when price/news download works.
            pass

    if not long_name and not short_name and ticker in COMPANY_NAME_OVERRIDES:
        long_name = COMPANY_NAME_OVERRIDES[ticker]

    display_name = long_name or short_name or ticker
    aliases = _company_aliases_from_names(ticker, long_name, short_name, display_name)
    if not aliases and ticker:
        aliases = [ticker]

    return {
        "ticker": ticker,
        "company_name": display_name,
        "long_name": long_name,
        "short_name": short_name,
        "aliases": aliases,
        "exchange": exchange,
        "quote_type": quote_type,
        "sector": sector,
        "industry": industry,
        "ambiguous_ticker": ticker in AMBIGUOUS_TICKERS or len(ticker) <= 2,
    }


def _newsapi_query_for_profile(profile: dict[str, Any]) -> str:
    """Build a company-name-first NewsAPI query."""
    ticker = str(profile.get("ticker") or "").upper()
    aliases = [a for a in profile.get("aliases", []) if a]

    phrase_parts: list[str] = []
    for alias in aliases[:5]:
        # Raw tickers are useful for AAPL/MSFT but dangerous for PLAY/ON/GO.
        if alias.upper() == ticker and profile.get("ambiguous_ticker"):
            continue
        phrase_parts.append(f'"{alias}"' if " " in alias or "&" in alias or "'" in alias else alias)

    if ticker and not profile.get("ambiguous_ticker"):
        phrase_parts.append(ticker)

    if not phrase_parts:
        phrase_parts = [ticker]

    # Company phrase first, then finance context. This avoids generic word matches like PLAY in sports/entertainment.
    company_part = " OR ".join(dict.fromkeys(phrase_parts))
    finance_part = 'stock OR shares OR earnings OR revenue OR analyst OR "price target" OR investors OR NYSE OR NASDAQ'
    return f"({company_part}) AND ({finance_part})"


def _ticker_context_match(text: str, ticker: str) -> bool:
    ticker = str(ticker or "").upper().strip()
    if not ticker:
        return False
    patterns = [
        rf"\({re.escape(ticker)}\)",
        rf"\bNYSE\s*[:\-]?\s*{re.escape(ticker)}\b",
        rf"\bNASDAQ\s*[:\-]?\s*{re.escape(ticker)}\b",
        rf"\b{re.escape(ticker)}\s+(stock|shares|earnings|analyst|price target)\b",
    ]
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _finance_context_score(text: str) -> int:
    lower = text.lower()
    return sum(1 for term in FINANCE_CONTEXT_TERMS if term in lower)


def score_news_relevance(row: dict[str, Any] | pd.Series, profile: dict[str, Any]) -> float:
    """Score how likely a headline is actually about the selected company."""
    title = str(row.get("title", "") or "")
    summary = str(row.get("summary", "") or "")
    url = str(row.get("url", "") or "")
    text = f"{title} {summary} {url}"
    compact_text = _compact_company_phrase(text)
    ticker = str(profile.get("ticker") or "").upper()
    aliases = profile.get("aliases", []) or []

    score = 0.0
    matched_alias = False
    for alias in aliases:
        alias_key = _compact_company_phrase(alias)
        if not alias_key:
            continue
        # Avoid matching tiny/generic aliases like "play" unless it appears in ticker context.
        if alias_key == ticker.lower() and profile.get("ambiguous_ticker"):
            continue
        if alias_key in compact_text:
            score += 6.0 if len(alias_key.split()) >= 2 else 3.0
            matched_alias = True
            break

    if _ticker_context_match(text, ticker):
        score += 3.0

    finance_score = _finance_context_score(text)
    if finance_score:
        score += min(2.0, finance_score * 0.5)

    # Company endpoint sources deserve a small trust bump, but not enough to keep unrelated broad NewsAPI rows.
    source = str(row.get("source", "") or "").lower()
    if source in {"finnhub", "yfinance"}:
        score += 1.0

    # If there is no company/ticker match, finance context alone is not enough.
    if not matched_alias and not _ticker_context_match(text, ticker):
        return min(score, 2.0)

    return float(score)


def filter_relevant_news(df: pd.DataFrame, profile: dict[str, Any], max_items: int = 20, min_score: float = 4.0) -> pd.DataFrame:
    """Filter broad news results to company-relevant items."""
    if df is None or df.empty:
        return pd.DataFrame()

    data = df.copy()
    data["relevance_score"] = data.apply(lambda row: score_news_relevance(row, profile), axis=1)
    data["company_name"] = profile.get("company_name") or profile.get("ticker")
    data["company_aliases"] = ", ".join(profile.get("aliases", [])[:5])

    # yfinance and Finnhub are already ticker/company endpoints, but still remove obviously irrelevant rows.
    # NewsAPI is broad search, so it must satisfy the same relevance threshold.
    filtered = data[data["relevance_score"] >= min_score].copy()
    if filtered.empty:
        return filtered

    filtered["published_at"] = pd.to_datetime(filtered["published_at"], errors="coerce")
    return filtered.sort_values(["published_at", "relevance_score"], ascending=[False, False]).head(max_items).reset_index(drop=True)


def fetch_yfinance_news(ticker: str, max_items: int = 20) -> pd.DataFrame:
    """Fetch recent ticker news from yfinance. No API key, no billing."""
    ticker = ticker.strip().upper()
    if not ticker:
        return pd.DataFrame()

    if yf is None:
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

    raw_df = pd.DataFrame(rows)
    profile = resolve_company_profile(ticker)
    return filter_relevant_news(raw_df, profile, max_items=max_items, min_score=4.0)


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
    for item in items:
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
    raw_df = pd.DataFrame(rows)
    profile = resolve_company_profile(ticker)
    return filter_relevant_news(raw_df, profile, max_items=max_items, min_score=3.5)


def fetch_newsapi_news(ticker: str, max_items: int = 20, days_back: int = 14) -> pd.DataFrame:
    """Fetch recent news from NewsAPI Developer API when NEWSAPI_API_KEY is configured."""
    api_key = _get_env_value("NEWSAPI_API_KEY")
    if not api_key:
        return pd.DataFrame()

    ticker = ticker.strip().upper()
    profile = resolve_company_profile(ticker)
    query = _newsapi_query_for_profile(profile)
    from_date = (datetime.utcnow().date() - timedelta(days=days_back)).isoformat()
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "searchIn": "title,description",
        "from": from_date,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": min(max_items * 3, 100),
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
    for item in items:
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
    raw_df = pd.DataFrame(rows)
    return filter_relevant_news(raw_df, profile, max_items=max_items, min_score=4.0)


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
    profile = resolve_company_profile(ticker)
    meta: dict[str, Any] = {
        "requested_source": source,
        "source_used": None,
        "sources_used": [],
        "api_key_required": source in {"finnhub", "newsapi"},
        "api_key_found": False,
        "fallback_used": False,
        "cache_used": False,
        "company_name": profile.get("company_name") or ticker,
        "company_aliases": profile.get("aliases", []),
        "newsapi_query": _newsapi_query_for_profile(profile),
        "relevance_filter": "company-name/ticker-context relevance filter enabled",
        "notes": [],
    }

    if use_cache and not force_refresh:
        cached = load_news_from_cache(ticker=ticker, max_age_hours=cache_max_age_hours, max_items=max_items)
        if not cached.empty:
            cached_count = len(cached)
            cached = filter_relevant_news(cached, profile, max_items=max_items, min_score=4.0)
            if not cached.empty:
                meta["source_used"] = "local_cache"
                meta["sources_used"] = sorted(cached["source"].dropna().astype(str).unique().tolist())
                meta["cache_used"] = True
                removed = cached_count - len(cached)
                meta["notes"].append(f"Used local news cache younger than {cache_max_age_hours:g} hours.")
                if removed > 0:
                    meta["notes"].append(f"Relevance filter removed {removed} cached unrelated headline(s).")
                return cached, meta
            meta["notes"].append("Cached headlines were present but none passed company relevance filtering; refreshing news.")

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


def _keyword_hits(text: str, patterns: list[tuple[str, str]]) -> list[str]:
    return [tag for tag, pattern in patterns if re.search(pattern, text, flags=re.IGNORECASE)]


def _target_mentioned(text: str, ticker: str, company_name: str, aliases: list[str]) -> bool:
    profile = {
        "ticker": ticker,
        "company_name": company_name,
        "aliases": aliases or ([company_name] if company_name else []),
        "ambiguous_ticker": str(ticker).upper() in AMBIGUOUS_TICKERS or len(str(ticker)) <= 2,
    }
    row = {"title": text, "summary": "", "url": ""}
    return score_news_relevance(row, profile) >= 3.0


def apply_target_aware_sentiment(row: dict[str, Any], base: SentimentResult) -> dict[str, Any]:
    """Correct generic sentiment into ticker-targeted financial sentiment.

    Generic sentiment often mistakes phrases such as "X is risky and one stock to
    buy instead" as positive because the words "stock to buy" are positive in
    isolation. This layer asks the product question instead: is the headline
    positive or negative for the selected ticker/company?
    """
    title = str(row.get("title", "") or "")
    summary = str(row.get("summary", "") or "")
    text = f"{title}. {summary}".strip()
    compact = _compact_company_phrase(text)
    ticker = str(row.get("ticker", "") or "").upper().strip()
    company_name = str(row.get("company_name", "") or ticker).strip()
    aliases_text = str(row.get("company_aliases", "") or "")
    aliases = [part.strip() for part in aliases_text.split(",") if part.strip()]
    if company_name and company_name not in aliases:
        aliases.insert(0, company_name)

    relevance_score = float(row.get("relevance_score", 0.0) or 0.0)
    finance_context = _finance_context_score(text)
    ticker_context = _ticker_context_match(text, ticker)
    if relevance_score >= 6.0:
        relevance_label = "High"
    elif relevance_score >= 4.0:
        relevance_label = "Medium"
    elif _target_mentioned(text, ticker, company_name, aliases) and (finance_context > 0 or ticker_context):
        relevance_label = "Medium"
        relevance_score = max(relevance_score, 4.0)
    else:
        relevance_label = "Low"

    reason_tags: list[str] = []
    negative_hits = _keyword_hits(text, TARGET_NEGATIVE_PATTERNS)
    positive_hits = _keyword_hits(text, TARGET_POSITIVE_PATTERNS)

    # Target-aware inversion: the selected company is explicitly framed as the
    # thing to avoid, while another stock is the one to buy instead.
    buy_instead = "buy instead" in compact or "stock to buy instead" in compact or "stocks to buy instead" in compact
    target_name_near_risk = False
    for alias in aliases + ([ticker] if ticker else []):
        alias_key = _compact_company_phrase(alias)
        if not alias_key:
            continue
        pattern = rf"{re.escape(alias_key)}.{{0,80}}\b(risky|risk|avoid|caution|bearish|underperform|sell|warning)\b"
        if re.search(pattern, compact):
            target_name_near_risk = True
            break

    target_label = base.label
    score = float(base.score)
    confidence = float(base.confidence)
    explanation = "Generic financial sentiment score accepted."

    if relevance_label == "Low":
        target_label = IRRELEVANT_LABEL
        score = 0.0
        confidence = min(confidence, 0.35)
        reason_tags = ["low-target-relevance"]
        explanation = "Headline did not strongly match the selected company, so it is treated as low-relevance context."
    elif buy_instead and (target_name_near_risk or "risk-language" in negative_hits):
        target_label = CAUTIONARY_LABEL
        score = min(score, -0.55)
        confidence = max(confidence, 0.82)
        reason_tags = ["buy-alternative-framing", "risk-language"]
        explanation = "The selected company is described as risky while the headline recommends another stock instead."
    elif negative_hits and not positive_hits:
        target_label = CAUTIONARY_LABEL
        score = min(score, -0.35)
        confidence = max(confidence, 0.68)
        reason_tags = negative_hits
        explanation = "Headline contains cautionary language tied to the selected company."
    elif positive_hits and not negative_hits:
        target_label = "Positive"
        score = max(score, 0.30)
        confidence = max(confidence, 0.62)
        reason_tags = positive_hits
        explanation = "Headline contains positive event language tied to the selected company."
    elif positive_hits and negative_hits:
        # Mixed headlines are common. Avoid pretending precision when both sides appear.
        if score <= -0.12:
            target_label = CAUTIONARY_LABEL
        elif score >= 0.12:
            target_label = "Positive"
        else:
            target_label = UNCERTAIN_LABEL
        confidence = min(max(confidence, 0.55), 0.72)
        reason_tags = list(dict.fromkeys(negative_hits + positive_hits + ["mixed-event-language"]))
        explanation = "Headline contains both positive and cautionary event language, so confidence is capped."
    elif abs(score) < 0.12:
        target_label = "Neutral"
        reason_tags = ["no-strong-directional-event"]
        explanation = "No strong target-specific financial event language was detected."

    # Keep the existing three-class sentiment_label for downstream scoring, but
    # expose a richer target_sentiment_label for the UI and diagnostics.
    normalized_label = target_label
    if target_label in {CAUTIONARY_LABEL, "Negative"}:
        normalized_label = "Negative"
    elif target_label == "Positive":
        normalized_label = "Positive"
    elif target_label in {IRRELEVANT_LABEL, UNCERTAIN_LABEL}:
        normalized_label = "Neutral"

    return {
        "sentiment_label": normalized_label,
        "sentiment_score": float(max(-1.0, min(1.0, score))),
        "confidence": float(max(0.0, min(0.98, confidence))),
        "target_sentiment_label": target_label,
        "target_relevance_label": relevance_label,
        "target_relevance_score": float(relevance_score),
        "reason_tags": ", ".join(dict.fromkeys(reason_tags)),
        "sentiment_explanation": explanation,
        "target_company": company_name or ticker,
        "target_ticker": ticker,
        "base_sentiment_label": base.label,
        "base_sentiment_score": float(base.score),
    }


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
        target_adjusted = apply_target_aware_sentiment(enriched, result)
        adjusted_score = float(target_adjusted["sentiment_score"])
        positive_probability = max(0.0, adjusted_score)
        negative_probability = max(0.0, -adjusted_score)
        neutral_probability = max(0.0, 1.0 - positive_probability - negative_probability)
        total_probability = positive_probability + neutral_probability + negative_probability or 1.0

        enriched.update(
            {
                **target_adjusted,
                "positive_probability": float(positive_probability / total_probability),
                "neutral_probability": float(neutral_probability / total_probability),
                "negative_probability": float(negative_probability / total_probability),
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
    """Aggregate headline sentiment into a dashboard summary.

    The headline-level DataFrame may include target-aware labels such as
    Cautionary, Irrelevant, and Uncertain. Aggregation uses only target-relevant
    rows when available so unrelated or ambiguous headlines do not distort the
    ticker-level overlay.
    """
    if sentiment_df is None or sentiment_df.empty or "sentiment_label" not in sentiment_df.columns:
        return {
            "available": False,
            "headline_count": 0,
            "scored_headline_count": 0,
            "overall_label": "No news",
            "average_score": 0.0,
            "positive_count": 0,
            "neutral_count": 0,
            "negative_count": 0,
            "cautionary_count": 0,
            "irrelevant_count": 0,
            "uncertain_count": 0,
            "confidence": 0.0,
            "agreement": None,
            "engine": "none",
            "source_used": "none",
        }

    data = sentiment_df.copy()
    headline_count = len(data)
    if "target_sentiment_label" in data.columns:
        target_labels_all = data["target_sentiment_label"].astype(str)
        irrelevant_mask = target_labels_all.isin([IRRELEVANT_LABEL, UNCERTAIN_LABEL])
        scored = data.loc[~irrelevant_mask].copy()
        if scored.empty:
            scored = data.copy()
    else:
        target_labels_all = data["sentiment_label"].astype(str)
        scored = data.copy()

    count = len(scored)
    labels = scored["sentiment_label"].astype(str)
    target_labels = scored.get("target_sentiment_label", labels).astype(str)
    positive_count = int((labels == "Positive").sum())
    neutral_count = int((labels == "Neutral").sum())
    negative_count = int((labels == "Negative").sum())
    cautionary_count = int((target_labels_all == CAUTIONARY_LABEL).sum())
    irrelevant_count = int((target_labels_all == IRRELEVANT_LABEL).sum())
    uncertain_count = int((target_labels_all == UNCERTAIN_LABEL).sum())
    average_score = float(pd.to_numeric(scored["sentiment_score"], errors="coerce").fillna(0.0).mean()) if count else 0.0
    confidence = float(pd.to_numeric(scored["confidence"], errors="coerce").fillna(0.0).mean()) if count else 0.0

    agreement_value = None
    if "model_agreement" in scored.columns:
        agreements = pd.to_numeric(scored["model_agreement"], errors="coerce").dropna()
        if not agreements.empty:
            agreement_value = float(agreements.mean())

    if average_score >= 0.12:
        overall_label = "Positive"
    elif average_score <= -0.12:
        overall_label = "Negative"
    else:
        overall_label = "Neutral"

    display_label = overall_label
    if overall_label == "Negative" and cautionary_count >= max(1, negative_count // 2):
        display_label = CAUTIONARY_LABEL

    engine = "mixed"
    if "sentiment_engine" in scored.columns and not scored["sentiment_engine"].dropna().empty:
        engines = scored["sentiment_engine"].dropna().astype(str).unique().tolist()
        engine = engines[0] if len(engines) == 1 else "mixed"

    source_used = "mixed"
    if "source" in scored.columns and not scored["source"].dropna().empty:
        sources = scored["source"].dropna().astype(str).unique().tolist()
        source_used = sources[0] if len(sources) == 1 else "mixed"

    return {
        "available": True,
        "headline_count": headline_count,
        "scored_headline_count": count,
        "average_score": average_score,
        "positive_count": positive_count,
        "neutral_count": neutral_count,
        "negative_count": negative_count,
        "cautionary_count": cautionary_count,
        "irrelevant_count": irrelevant_count,
        "uncertain_count": uncertain_count,
        "positive_ratio": positive_count / count if count else 0.0,
        "negative_ratio": negative_count / count if count else 0.0,
        "overall_label": overall_label,
        "display_label": display_label,
        "confidence": confidence,
        "agreement": agreement_value,
        "engine": engine,
        "source_used": source_used,
    }


def sentiment_context_sentence(summary: dict[str, Any]) -> str:
    """Return a human-readable interpretation for the UI."""
    if not summary.get("available"):
        return "No recent headlines were returned for this ticker. Meroq can still run price, model, and risk analysis."

    label = summary.get("display_label", summary.get("overall_label", "Neutral")).lower()
    agreement = summary.get("agreement")
    agreement_text = f" Average model agreement is {agreement:.1%}." if agreement is not None else ""
    scored_count = summary.get("scored_headline_count", summary.get("headline_count", 0))
    excluded = int(summary.get("irrelevant_count", 0) or 0) + int(summary.get("uncertain_count", 0) or 0)
    excluded_text = f" {excluded} low-relevance/uncertain headline(s) were excluded from the overlay." if excluded else ""
    return (
        f"Recent target-aware headline sentiment is **{label}** across {scored_count} scored headlines. "
        f"Average sentiment score is {summary['average_score']:+.2f}, with "
        f"{summary['positive_count']} positive, {summary['neutral_count']} neutral, and "
        f"{summary['negative_count']} cautionary/negative headlines.{excluded_text}{agreement_text}"
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
