"use client";

import { FormEvent, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { MetricCard } from "@/components/MetricCard";
import { PageShell } from "@/components/PageShell";
import { analyzePortfolio, parseTickerList, type ApiRecord } from "@/lib/api";

function pct(value: unknown) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "N/A";
  return `${(number * 100).toFixed(1)}%`;
}

export default function PortfolioPage() {
  const [tickers, setTickers] = useState("AAPL,MSFT,NVDA,SPY");
  const [weights, setWeights] = useState("AAPL:30,MSFT:25,NVDA:25,SPY:20");
  const [holdings, setHoldings] = useState<ApiRecord[]>([]);
  const [summary, setSummary] = useState<ApiRecord | null>(null);
  const [sentence, setSentence] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setHoldings([]);
    setSummary(null);
    setSentence("");

    try {
      const response = await analyzePortfolio({
        tickers: parseTickerList(tickers),
        weights,
        period: "5y",
        interval: "1d",
        include_sentiment: true,
        include_risk: true,
        max_news_items: 10,
        risk_paths: 300,
      });
      setHoldings(response.holdings);
      setSummary(response.summary);
      setSentence(response.summary_sentence);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Portfolio analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PageShell>
      <section className="hero">
        <h1>Portfolio view</h1>
        <p>Analyze weighted exposure from a watchlist scan through the FastAPI backend.</p>
      </section>

      <form className="card form" onSubmit={onSubmit}>
        <label>
          Tickers
          <textarea rows={2} value={tickers} onChange={(event) => setTickers(event.target.value)} />
        </label>
        <label>
          Weights
          <textarea rows={2} value={weights} onChange={(event) => setWeights(event.target.value)} />
        </label>
        <button disabled={loading}>{loading ? "Analyzing..." : "Analyze portfolio"}</button>
      </form>

      {error ? <p className="error">{error}</p> : null}

      {summary ? (
        <>
          <section className="grid cols-3" style={{ marginTop: 18 }}>
            <MetricCard label="Holdings" value={String(summary.holding_count ?? holdings.length)} />
            <MetricCard label="Weighted Meroq score" value={String(summary.weighted_meroq_score ?? "N/A")} />
            <MetricCard label="Weighted downside risk" value={pct(summary.weighted_downside_probability)} />
          </section>
          <section className="card" style={{ marginTop: 18 }}>
            <h2>Summary</h2>
            <p className="muted">{sentence}</p>
          </section>
        </>
      ) : null}

      <section className="card" style={{ marginTop: 18 }}>
        <h2>Holdings</h2>
        <DataTable rows={holdings} />
      </section>
    </PageShell>
  );
}
