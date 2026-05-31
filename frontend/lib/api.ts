export const API_BASE =
  process.env.NEXT_PUBLIC_MEROQ_API_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

export type ApiValue = string | number | boolean | null | undefined;
export type ApiRecord = Record<string, ApiValue>;

export type HealthResponse = {
  status?: string;
  app?: string;
  version?: string;
  generated_at_utc?: string;
};

export type TickerAnalysisPayload = {
  ticker: string;
  period: string;
  interval: string;
  model_name?: string;
  include_risk?: boolean;
  include_news?: boolean;
  include_sentiment_fusion?: boolean;
  news_source?: string;
  sentiment_engine?: string;
  max_news_items?: number;
  news_lookback_days?: number;
  simulation_horizon?: number;
  simulation_paths?: number;
  volatility_window?: number;
  return_details?: boolean;
};

export type TickerAnalysisResponse = {
  summary: ApiRecord;
  request: ApiRecord;
  details?: {
    prediction?: ApiRecord;
    sentiment_summary?: ApiRecord;
    sentiment_fusion?: ApiRecord;
    risk_summary?: ApiRecord;
    risk_percentiles?: ApiRecord[];
    news_meta?: ApiRecord;
    news_headlines?: ApiRecord[];
  };
};

export type WatchlistPayload = {
  tickers: string[];
  period: string;
  interval: string;
  include_sentiment?: boolean;
  include_risk?: boolean;
  news_source?: string;
  sentiment_engine?: string;
  max_news_items?: number;
  risk_paths?: number;
  risk_horizon?: number;
  days_back?: number;
};

export type PortfolioPayload = WatchlistPayload & {
  weights?: string;
};

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (body.detail) detail = String(body.detail);
    } catch {
      // Keep the HTTP status message.
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export function getHealth() {
  return apiFetch<HealthResponse>("/health");
}

export function getMetadata() {
  return apiFetch<Record<string, unknown>>("/metadata");
}

export function analyzeTicker(payload: TickerAnalysisPayload) {
  return apiFetch<TickerAnalysisResponse>("/analysis/ticker", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function scanWatchlist(payload: WatchlistPayload) {
  return apiFetch<{ summary: ApiRecord; rows: ApiRecord[] }>("/watchlist/scan", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function analyzePortfolio(payload: PortfolioPayload) {
  return apiFetch<{ summary: ApiRecord; summary_sentence: string; holdings: ApiRecord[]; scan_rows: ApiRecord[] }>(
    "/portfolio/analyze",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function parseTickerList(value: string): string[] {
  return value
    .split(/[\n,]+/)
    .map((item) => item.trim().toUpperCase())
    .filter(Boolean);
}

export function formatPct(value: unknown, decimals = 1) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "N/A";
  return `${(number * 100).toFixed(decimals)}%`;
}

export function formatSignedPctPoints(value: unknown) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "N/A";
  return `${number >= 0 ? "+" : ""}${number.toFixed(2)} pp`;
}

export function formatMoney(value: unknown) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "N/A";
  return `$${number.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

export function formatNumber(value: unknown, decimals = 2) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "N/A";
  return number.toLocaleString(undefined, { maximumFractionDigits: decimals });
}
