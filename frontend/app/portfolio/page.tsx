"use client";

import { FormEvent, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { ErrorBox, LoadingState } from "@/components/StateBlocks";
import { MetricCard } from "@/components/MetricCard";
import { PageShell } from "@/components/PageShell";
import { analyzePortfolio, formatNumber, formatPct, parseTickerList, type ApiRecord } from "@/lib/api";

const holdingColumns = [
  "ticker",
  "weight",
  "latest_close",
  "final_signal",
  "final_up_probability",
  "risk_label",
  "risk_loss_gt_5pct",
  "meroq_score",
];

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
        news_source: "all_configured",
        sentiment_engine: "lightweight",
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
      <section className="hero compact-hero">
        <p className="eyebrow">Portfolio view</p>
        <h1>Turn watchlist signals into weighted exposure.</h1>
        <p>Use custom weights to see which positions drive score, sentiment, and downside risk.</p>
      </section>

      <form className="card form" onSubmit={onSubmit}>
        <label>
          Portfolio tickers
          <textarea rows={2} value={tickers} onChange={(event) => setTickers(event.target.value)} />
        </label>
        <label>
          Weights
          <textarea rows={2} value={weights} onChange={(event) => setWeights(event.target.value)} />
        </label>
        <p className="muted small">Format: AAPL:30, MSFT:25, NVDA:25, SPY:20. Blank weights default to equal weight.</p>
        <button disabled={loading}>{loading ? "Analyzing..." : "Analyze portfolio"}</button>
      </form>

      {loading ? <LoadingState label="Analyzing portfolio..." /> : null}
      {error ? <ErrorBox message={error} /> : null}

      {summary ? (
        <>
          <section className="grid cols-4" style={{ marginTop: 18 }}>
            <MetricCard label="Holdings" value={String(summary.holding_count ?? holdings.length)} />
            <MetricCard label="Weighted Meroq score" value={formatNumber(summary.weighted_meroq_score)} />
            <MetricCard label="Weighted up probability" value={formatPct(summary.weighted_up_probability)} />
            <MetricCard label="Downside exposure" value={formatPct(summary.weighted_downside_probability)} />
          </section>
          <section className="card callout-card" style={{ marginTop: 18 }}>
            <p className="status-label">Portfolio read</p>
            <h2>{String(summary.portfolio_signal_label ?? "Balanced exposure")}</h2>
            <p className="muted">{sentence}</p>
          </section>
        </>
      ) : null}

      <section className="card" style={{ marginTop: 18 }}>
        <h2>Holdings</h2>
        <DataTable rows={holdings} columns={holdingColumns} />
      </section>
    </PageShell>
  );
}
