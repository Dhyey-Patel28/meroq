export const API_BASE =
  process.env.NEXT_PUBLIC_MEROQ_API_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

export type ApiRecord = Record<string, string | number | boolean | null | undefined>;

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
  simulation_paths?: number;
  return_details?: boolean;
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
      // Keep HTTP status message.
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export function getHealth() {
  return apiFetch<ApiRecord>("/health");
}

export function getMetadata() {
  return apiFetch<Record<string, unknown>>("/metadata");
}

export function analyzeTicker(payload: TickerAnalysisPayload) {
  return apiFetch<{ summary: ApiRecord; request: ApiRecord; details?: Record<string, unknown> }>(
    "/analysis/ticker",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
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
    .split(",")
    .map((item) => item.trim().toUpperCase())
    .filter(Boolean);
}
