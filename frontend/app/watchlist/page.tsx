"use client";

import { FormEvent, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { ErrorBox, LoadingState } from "@/components/StateBlocks";
import { MetricCard } from "@/components/MetricCard";
import { PageShell } from "@/components/PageShell";
import { formatNumber, parseTickerList, scanWatchlist, type ApiRecord } from "@/lib/api";

const columns = [
  "ticker",
  "latest_close",
  "final_signal",
  "final_up_probability",
  "sentiment_label",
  "risk_label",
  "meroq_score",
];

export default function WatchlistPage() {
  const [tickers, setTickers] = useState("AAPL,MSFT,NVDA,GOOGL,SPY");
  const [period, setPeriod] = useState("5y");
  const [rows, setRows] = useState<ApiRecord[]>([]);
  const [summary, setSummary] = useState<ApiRecord | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setRows([]);
    setSummary(null);

    try {
      const response = await scanWatchlist({
        tickers: parseTickerList(tickers),
        period,
        interval: "1d",
        include_sentiment: true,
        include_risk: true,
        news_source: "all_configured",
        sentiment_engine: "lightweight",
        max_news_items: 10,
        risk_paths: 300,
        risk_horizon: 30,
      });
      setRows(response.rows);
      setSummary(response.summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Watchlist scan failed.");
    } finally {
      setLoading(false);
    }
  }

  const top = rows.slice(0, 3).map((row) => String(row.ticker)).join(", ");

  return (
    <PageShell>
      <section className="hero compact-hero">
        <p className="eyebrow">Watchlist scan</p>
        <h1>Rank a small universe by signal, sentiment, and risk.</h1>
        <p>Designed for idea discovery. Keep the first scan small while developing locally.</p>
      </section>

      <form className="card form" onSubmit={onSubmit}>
        <label>
          Watchlist tickers
          <textarea rows={3} value={tickers} onChange={(event) => setTickers(event.target.value)} />
        </label>
        <label>
          History period
          <select value={period} onChange={(event) => setPeriod(event.target.value)}>
            <option value="1y">1y</option>
            <option value="5y">5y</option>
            <option value="10y">10y</option>
            <option value="max">max</option>
          </select>
        </label>
        <button disabled={loading}>{loading ? "Scanning..." : "Run watchlist scan"}</button>
      </form>

      {loading ? <LoadingState label="Scanning watchlist..." /> : null}
      {error ? <ErrorBox message={error} /> : null}

      {summary ? (
        <section className="grid cols-4" style={{ marginTop: 18 }}>
          <MetricCard label="Scanned" value={String(summary.tickers_scanned ?? rows.length)} />
          <MetricCard label="Bullish names" value={String(summary.bullish_count ?? "N/A")} />
          <MetricCard label="Positive sentiment" value={String(summary.positive_sentiment_count ?? "N/A")} />
          <MetricCard label="High risk" value={String(summary.high_risk_count ?? "N/A")} />
        </section>
      ) : null}

      {rows.length ? (
        <section className="card callout-card" style={{ marginTop: 18 }}>
          <p className="status-label">Quick read</p>
          <h2>Highest-ranked: {top || "N/A"}</h2>
          <p className="muted">Top rows are sorted by Meroq score. Compare score with risk label before treating any name as attractive.</p>
        </section>
      ) : null}

      <section className="card" style={{ marginTop: 18 }}>
        <div className="card-heading-row">
          <h2>Ranked scan</h2>
          {rows.length ? <span className="muted small">Top score: {formatNumber(rows[0]?.meroq_score)}</span> : null}
        </div>
        <DataTable rows={rows} columns={columns} />
      </section>
    </PageShell>
  );
}
