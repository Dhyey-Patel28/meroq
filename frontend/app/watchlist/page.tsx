"use client";

import { FormEvent, useMemo, useRef, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { StockDetailModal } from "@/components/StockDetailModal";
import { ErrorBox } from "@/components/StateBlocks";
import { MetricCard } from "@/components/MetricCard";
import { PageShell } from "@/components/PageShell";
import {
  formatNumber,
  parseTickerList,
  scanWatchlistOne,
  type ApiRecord,
  type WatchlistSinglePayload,
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
  "note",
];

function buildSummary(rows: ApiRecord[]) {
  const okRows = rows.filter((row) => String(row.status ?? "").toLowerCase() === "ok");
  return {
    scanned: rows.length,
    ready: okRows.length,
    issues: rows.length - okRows.length,
    bullish: okRows.filter((row) => String(row.final_signal ?? "").toLowerCase() === "bullish").length,
    highRisk: okRows.filter((row) => String(row.risk_label ?? "").toLowerCase().includes("high")).length,
  };
}

function sortRows(rows: ApiRecord[]) {
  return [...rows].sort((a, b) => {
    const aOk = String(a.status ?? "") === "ok" ? 1 : 0;
    const bOk = String(b.status ?? "") === "ok" ? 1 : 0;
    if (aOk !== bOk) return bOk - aOk;
    return Number(b.meroq_score ?? -Infinity) - Number(a.meroq_score ?? -Infinity);
  });
}

export default function WatchlistPage() {
  const [tickers, setTickers] = useState("AAPL,MSFT,NVDA,GOOGL,SPY");
  const [period, setPeriod] = useState("5y");
  const [maxTickers, setMaxTickers] = useState(40);
  const [rows, setRows] = useState<ApiRecord[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentTicker, setCurrentTicker] = useState("");
  const [selectedRow, setSelectedRow] = useState<ApiRecord | null>(null);
  const stopRef = useRef(false);

  const summary = useMemo(() => buildSummary(rows), [rows]);
  const sortedRows = useMemo<ApiRecord[]>(
    () =>
      sortRows(rows).map((row) => ({
        ...row,
        note:
          String(row.status ?? "") === "failed"
            ? row.error ?? "Data issue"
            : row.headline_count
              ? `${String(row.headline_count)} headlines reviewed`
              : "Ready",
      })),
    [rows],
  );

  const top = sortedRows
    .filter((row) => String(row.status ?? "") === "ok")
    .slice(0, 3)
    .map((row) => String(row.ticker))
    .join(", ");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setRows([]);
    setCurrentTicker("");
    stopRef.current = false;

    const symbols = parseTickerList(tickers).slice(0, Math.max(1, maxTickers));
    const basePayload: Omit<WatchlistSinglePayload, "ticker"> = {
      period,
      interval: "1d",
      include_sentiment: true,
      include_risk: true,
      news_source: "all_configured",
      sentiment_engine: "lightweight",
      max_news_items: 10,
      risk_paths: 300,
      risk_horizon: 30,
      days_back: 7,
    };

    try {
      for (const symbol of symbols) {
        if (stopRef.current) break;
        setCurrentTicker(symbol);
        const response = await scanWatchlistOne({ ...basePayload, ticker: symbol });
        setRows((current) => [...current, response.row]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Watchlist scan failed.");
    } finally {
      stopRef.current = false;
      setLoading(false);
      setCurrentTicker("");
    }
  }

  return (
    <PageShell>
      <section className="hero compact-hero">
        <p className="eyebrow">Watchlist scan</p>
        <h1>Rank a working watchlist as rows finish loading.</h1>
        <p>Good rows appear immediately, failed symbols are marked with a compact issue note, and every row is searchable.</p>
      </section>

      <form className="card form" onSubmit={onSubmit}>
        <label>
          Watchlist tickers
          <textarea rows={4} value={tickers} onChange={(event) => setTickers(event.target.value)} />
        </label>
        <div className="grid cols-2">
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
              max={200}
              value={maxTickers}
              onChange={(event) => setMaxTickers(Number(event.target.value) || 1)}
            />
          </label>
        </div>
        <div className="button-row">
          <button disabled={loading}>{loading ? "Scanning…" : "Run watchlist scan"}</button>
          <button
            type="button"
            className="secondary-button"
            disabled={!loading}
            onClick={() => {
              stopRef.current = true;
            }}
          >
            Stop scan
          </button>
        </div>
        <p className="muted small">
          Large local universes can take a while. Start with 25–40 names, then expand. Symbols that cannot be downloaded are skipped and labeled.
        </p>
      </form>

      {loading ? (
        <section className="card subtle-card" style={{ marginTop: 18 }}>
          <div className="loader-row">
            <span className="spinner" />
            <div>
              <h3>Scanning {currentTicker || "watchlist"}…</h3>
              <p className="muted">Rows are added as soon as each ticker finishes.</p>
            </div>
          </div>
          <div className="progress-inline">
            <div className="progress-track" aria-hidden="true">
              <div
                className="progress-fill"
                style={{ width: `${Math.min(100, (summary.scanned / Math.max(1, Math.min(parseTickerList(tickers).length, maxTickers))) * 100)}%` }}
              />
            </div>
            <span className="muted small">
              {summary.scanned}/{Math.min(parseTickerList(tickers).length, maxTickers)} completed
            </span>
          </div>
        </section>
      ) : null}

      {error ? <ErrorBox message={error} /> : null}

      {rows.length ? (
        <section className="grid cols-4" style={{ marginTop: 18 }}>
          <MetricCard label="Completed" value={String(summary.scanned)} helper="Rows returned so far" />
          <MetricCard label="Ready" value={String(summary.ready)} helper="Usable analyses" tone="positive" />
          <MetricCard label="Issues" value={String(summary.issues)} helper="Skipped or unavailable" tone={summary.issues ? "warning" : "neutral"} />
          <MetricCard label="Bullish" value={String(summary.bullish)} helper={`High risk names: ${summary.highRisk}`} />
        </section>
      ) : null}

      {rows.length ? (
        <section className="card callout-card" style={{ marginTop: 18 }}>
          <p className="status-label">Quick read</p>
          <h2>Highest-ranked ready names: {top || "Still loading"}</h2>
          <p className="muted">Use the legend below instead of raw status text. Click any row to open a richer ticker modal.</p>
        </section>
      ) : null}

      <section className="card" style={{ marginTop: 18 }}>
        <div className="card-heading-row">
          <div>
            <h2>Ranked scan</h2>
            <p className="muted small">Searchable, scrollable, and row-clickable.</p>
          </div>
          {sortedRows.length ? <span className="muted small">Top score: {formatNumber(sortedRows[0]?.meroq_score)}</span> : null}
        </div>
        <DataTable
          rows={sortedRows}
          columns={columns}
          searchPlaceholder="Search tickers, scores, signals, or issue notes…"
          onRowClick={(row) => setSelectedRow(row)}
          rowHint="Row details"
          legend={
            <div className="legend-row">
              <span className="legend-pill positive">▲ Bullish / positive</span>
              <span className="legend-pill warning">● Neutral / balanced</span>
              <span className="legend-pill negative">▼ Bearish / higher concern</span>
              <span className="legend-pill neutral">⚠ Data issue</span>
            </div>
          }
        />
      </section>

      <StockDetailModal ticker={selectedRow ? String(selectedRow.ticker ?? "") : null} period={period} baseRow={selectedRow} onClose={() => setSelectedRow(null)} />
    </PageShell>
  );
}
