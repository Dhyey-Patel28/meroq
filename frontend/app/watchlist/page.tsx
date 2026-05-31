"use client";

import { FormEvent, useMemo, useRef, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { ErrorBox } from "@/components/StateBlocks";
import { MetricCard } from "@/components/MetricCard";
import { PageShell } from "@/components/PageShell";
import {
  formatNumber,
  parseTickerList,
  scanWatchlistTicker,
  type ApiRecord,
} from "@/lib/api";

const columns = [
  "status",
  "ticker",
  "latest_close",
  "final_signal",
  "final_up_probability",
  "sentiment_label",
  "risk_label",
  "meroq_score",
  "error",
];

const DEFAULT_TICKERS = "AAPL,MSFT,NVDA,GOOGL,SPY,HOG,PLAY,QQQ,AMZN,TSLA";
const MAX_SCAN_LIMIT = 100;

function summarizeRows(rows: ApiRecord[]) {
  const okRows = rows.filter((row) => row.status === "ok");
  return {
    scanned: okRows.length,
    failed: rows.filter((row) => row.status === "failed").length,
    bullish: okRows.filter((row) => String(row.final_signal ?? "").toLowerCase() === "bullish").length,
    positiveSentiment: okRows.filter((row) => String(row.sentiment_label ?? "").toLowerCase() === "positive").length,
    highRisk: okRows.filter((row) => String(row.risk_label ?? "").toLowerCase().includes("high")).length,
  };
}

function sortByScore(rows: ApiRecord[]) {
  return [...rows].sort((a, b) => {
    const statusA = String(a.status ?? "");
    const statusB = String(b.status ?? "");
    if (statusA !== statusB) return statusA === "ok" ? -1 : 1;
    const scoreA = Number(a.meroq_score);
    const scoreB = Number(b.meroq_score);
    if (Number.isFinite(scoreA) && Number.isFinite(scoreB)) return scoreB - scoreA;
    if (Number.isFinite(scoreA)) return -1;
    if (Number.isFinite(scoreB)) return 1;
    return String(a.ticker ?? "").localeCompare(String(b.ticker ?? ""));
  });
}

export default function WatchlistPage() {
  const [tickers, setTickers] = useState(DEFAULT_TICKERS);
  const [period, setPeriod] = useState("5y");
  const [maxTickers, setMaxTickers] = useState(25);
  const [rows, setRows] = useState<ApiRecord[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentTicker, setCurrentTicker] = useState("");
  const [plannedTickers, setPlannedTickers] = useState<string[]>([]);
  const [skippedCount, setSkippedCount] = useState(0);
  const controllerRef = useRef<AbortController | null>(null);

  const rowSummary = useMemo(() => summarizeRows(rows), [rows]);
  const rankedRows = useMemo(() => sortByScore(rows), [rows]);
  const top = rankedRows
    .filter((row) => row.status === "ok")
    .slice(0, 3)
    .map((row) => String(row.ticker))
    .join(", ");

  const completedCount = rows.length;
  const totalCount = plannedTickers.length;
  const progressPct = totalCount ? Math.round((completedCount / totalCount) * 100) : 0;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();

    const parsed = parseTickerList(tickers);
    const limit = Math.max(1, Math.min(MAX_SCAN_LIMIT, Number(maxTickers) || 25));
    const planned = parsed.slice(0, limit);

    if (!planned.length) {
      setError("Add at least one ticker before running a scan.");
      return;
    }

    const controller = new AbortController();
    controllerRef.current = controller;

    setLoading(true);
    setError("");
    setRows([]);
    setCurrentTicker("");
    setPlannedTickers(planned);
    setSkippedCount(Math.max(0, parsed.length - planned.length));

    try {
      for (const ticker of planned) {
        if (controller.signal.aborted) break;
        setCurrentTicker(ticker);

        try {
          const response = await scanWatchlistTicker(
            {
              ticker,
              period,
              interval: "1d",
              include_sentiment: true,
              include_risk: true,
              news_source: "all_configured",
              sentiment_engine: "lightweight",
              max_news_items: 10,
              risk_paths: 250,
              risk_horizon: 30,
              days_back: 7,
            },
            controller.signal,
          );

          setRows((existing) => [...existing, response.row]);
        } catch (err) {
          if (controller.signal.aborted) break;
          setRows((existing) => [
            ...existing,
            {
              ticker,
              status: "failed",
              error: err instanceof Error ? `Unable to load data for ${ticker}: ${err.message}` : `Unable to load data for ${ticker}.`,
            },
          ]);
        }
      }
    } finally {
      setCurrentTicker("");
      setLoading(false);
      controllerRef.current = null;
    }
  }

  function stopScan() {
    controllerRef.current?.abort();
    setLoading(false);
    setCurrentTicker("");
  }

  return (
    <PageShell>
      <section className="hero compact-hero">
        <p className="eyebrow">Watchlist scan</p>
        <h1>Rank a focused universe by signal, sentiment, and risk.</h1>
        <p>Rows appear as each ticker finishes. Failed or unavailable tickers are shown and skipped so one bad symbol does not block the scan.</p>
      </section>

      <form className="card form watchlist-form" onSubmit={onSubmit}>
        <label>
          Watchlist tickers
          <textarea rows={5} value={tickers} onChange={(event) => setTickers(event.target.value)} />
        </label>
        <div className="form-two-col">
          <label>
            History period
            <select value={period} onChange={(event) => setPeriod(event.target.value)}>
              <option value="1y">1y</option>
              <option value="5y">5y</option>
              <option value="10y">10y</option>
              <option value="max">max</option>
            </select>
          </label>
          <label>
            Max tickers this scan
            <input
              type="number"
              min={1}
              max={MAX_SCAN_LIMIT}
              value={maxTickers}
              onChange={(event) => setMaxTickers(Number(event.target.value))}
            />
          </label>
        </div>
        <div className="button-row">
          <button disabled={loading}>{loading ? "Scanning..." : "Run progressive scan"}</button>
          {loading ? (
            <button type="button" className="secondary-button" onClick={stopScan}>
              Stop scan
            </button>
          ) : null}
        </div>
        <p className="muted small">
          Tip: start with 10–25 tickers. Very large lists can be slow because each symbol downloads prices, scores sentiment, and estimates risk.
        </p>
      </form>

      {error ? <ErrorBox message={error} /> : null}

      {totalCount ? (
        <section className="card scan-progress-card" style={{ marginTop: 18 }}>
          <div className="card-heading-row">
            <div>
              <p className="status-label">Progressive scan</p>
              <h2>{loading ? `Scanning ${currentTicker || "watchlist"}...` : "Scan progress"}</h2>
            </div>
            <span className="muted small">
              {completedCount}/{totalCount} complete
            </span>
          </div>
          <div className="progress-track" aria-label="Watchlist scan progress">
            <div className="progress-fill" style={{ width: `${progressPct}%` }} />
          </div>
          {skippedCount ? (
            <p className="muted small">
              {skippedCount} extra tickers were not scanned because of the current max-ticker limit.
            </p>
          ) : null}
        </section>
      ) : null}

      <section className="grid cols-4" style={{ marginTop: 18 }}>
        <MetricCard label="Loaded" value={String(rowSummary.scanned)} info="Tickers that returned usable market data and completed scoring." />
        <MetricCard label="Failed/skipped" value={String(rowSummary.failed)} info="Tickers that could not be downloaded or analyzed. They stay visible instead of blocking the scan." />
        <MetricCard label="Positive sentiment" value={String(rowSummary.positiveSentiment)} />
        <MetricCard label="High risk" value={String(rowSummary.highRisk)} />
      </section>

      {rankedRows.length ? (
        <section className="card callout-card" style={{ marginTop: 18 }}>
          <p className="status-label">Quick read</p>
          <h2>Highest-ranked: {top || "N/A"}</h2>
          <p className="muted">Successful rows are ranked by Meroq Score. Failed rows remain visible with an explanation so you can clean the ticker list.</p>
        </section>
      ) : null}

      <section className="card" style={{ marginTop: 18 }}>
        <div className="card-heading-row">
          <h2>Ranked scan</h2>
          {rankedRows.length ? <span className="muted small">Top score: {formatNumber(rankedRows[0]?.meroq_score)}</span> : null}
        </div>
        <DataTable rows={rankedRows} columns={columns} maxRows={100} />
      </section>
    </PageShell>
  );
}
