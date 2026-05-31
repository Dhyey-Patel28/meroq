"use client";

import { FormEvent, useState } from "react";
import { MetricCard } from "@/components/MetricCard";
import { PageShell } from "@/components/PageShell";
import { analyzeTicker, type ApiRecord } from "@/lib/api";

function pct(value: unknown) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "N/A";
  return `${(number * 100).toFixed(1)}%`;
}

function money(value: unknown) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "N/A";
  return `$${number.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

export default function TickerPage() {
  const [ticker, setTicker] = useState("AAPL");
  const [period, setPeriod] = useState("5y");
  const [interval, setInterval] = useState("1d");
  const [result, setResult] = useState<ApiRecord | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await analyzeTicker({
        ticker,
        period,
        interval,
        model_name: "xgboost",
        include_risk: true,
        include_news: true,
        include_sentiment_fusion: true,
        return_details: false,
      });
      setResult(response.summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PageShell>
      <section className="hero">
        <h1>Ticker analysis</h1>
        <p>Run the reusable Meroq analysis service through the FastAPI backend.</p>
      </section>

      <div className="grid cols-2">
        <form className="card form" onSubmit={onSubmit}>
          <label>
            Ticker
            <input value={ticker} onChange={(event) => setTicker(event.target.value.toUpperCase())} />
          </label>
          <label>
            Period
            <select value={period} onChange={(event) => setPeriod(event.target.value)}>
              <option value="1y">1y</option>
              <option value="5y">5y</option>
              <option value="10y">10y</option>
              <option value="max">max</option>
            </select>
          </label>
          <label>
            Interval
            <select value={interval} onChange={(event) => setInterval(event.target.value)}>
              <option value="1d">1d</option>
              <option value="1wk">1wk</option>
            </select>
          </label>
          <button disabled={loading}>{loading ? "Running..." : "Run analysis"}</button>
        </form>

        <section className="card">
          <h2>Result</h2>
          {!result && !error ? <p className="muted">Submit a ticker to see the API result.</p> : null}
          {error ? <p className="error">{error}</p> : null}
          {result ? (
            <div className="grid cols-2">
              <MetricCard label="Latest close" value={money(result.latest_close)} />
              <MetricCard label="Base signal" value={String(result.base_signal ?? "N/A")} />
              <MetricCard label="Base up probability" value={pct(result.base_up_probability)} />
              <MetricCard label="Final up probability" value={pct(result.final_up_probability)} />
              <MetricCard label="News sentiment" value={String(result.news_sentiment_label ?? "Skipped")} />
              <MetricCard label="Risk profile" value={String(result.risk_label ?? "Skipped")} />
            </div>
          ) : null}
        </section>
      </div>
    </PageShell>
  );
}
