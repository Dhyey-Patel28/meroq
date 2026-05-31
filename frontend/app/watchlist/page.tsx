"use client";

import { FormEvent, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { MetricCard } from "@/components/MetricCard";
import { PageShell } from "@/components/PageShell";
import { parseTickerList, scanWatchlist, type ApiRecord } from "@/lib/api";

export default function WatchlistPage() {
  const [tickers, setTickers] = useState("AAPL,MSFT,NVDA,SPY");
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
        period: "5y",
        interval: "1d",
        include_sentiment: true,
        include_risk: true,
        max_news_items: 10,
        risk_paths: 300,
      });
      setRows(response.rows);
      setSummary(response.summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Watchlist scan failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PageShell>
      <section className="hero">
        <h1>Watchlist scan</h1>
        <p>Rank a small universe using the Meroq API. Keep the list short while developing locally.</p>
      </section>

      <form className="card form" onSubmit={onSubmit}>
        <label>
          Tickers
          <textarea rows={3} value={tickers} onChange={(event) => setTickers(event.target.value)} />
        </label>
        <button disabled={loading}>{loading ? "Scanning..." : "Run watchlist scan"}</button>
      </form>

      {error ? <p className="error">{error}</p> : null}

      {summary ? (
        <section className="grid cols-3" style={{ marginTop: 18 }}>
          <MetricCard label="Scanned" value={String(summary.tickers_scanned ?? rows.length)} />
          <MetricCard label="Bullish" value={String(summary.bullish_count ?? "N/A")} />
          <MetricCard label="High risk" value={String(summary.high_risk_count ?? "N/A")} />
        </section>
      ) : null}

      <section className="card" style={{ marginTop: 18 }}>
        <h2>Ranked rows</h2>
        <DataTable rows={rows} />
      </section>
    </PageShell>
  );
}
