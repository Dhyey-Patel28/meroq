"use client";

import { FormEvent, useState } from "react";
import { ErrorBox, LoadingState } from "@/components/StateBlocks";
import { MetricCard } from "@/components/MetricCard";
import { PageShell } from "@/components/PageShell";
import { ProbabilityBar } from "@/components/ProbabilityBar";
import { StatusPill } from "@/components/StatusPill";
import {
  analyzeTicker,
  formatMoney,
  formatPct,
  formatSignedPctPoints,
  type TickerAnalysisResponse,
} from "@/lib/api";

function signalTone(signal: unknown): "neutral" | "positive" | "negative" | "warning" {
  const text = String(signal ?? "").toLowerCase();
  if (text.includes("bull")) return "positive";
  if (text.includes("bear")) return "negative";
  if (text.includes("neutral")) return "warning";
  return "neutral";
}

export default function TickerPage() {
  const [ticker, setTicker] = useState("AAPL");
  const [period, setPeriod] = useState("5y");
  const [interval, setInterval] = useState("1d");
  const [includeNews, setIncludeNews] = useState(true);
  const [includeRisk, setIncludeRisk] = useState(true);
  const [result, setResult] = useState<TickerAnalysisResponse | null>(null);
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
        include_risk: includeRisk,
        include_news: includeNews,
        include_sentiment_fusion: includeNews,
        news_source: "all_configured",
        sentiment_engine: "lightweight",
        max_news_items: 30,
        news_lookback_days: 14,
        simulation_paths: 500,
        return_details: true,
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  const summary = result?.summary;
  const details = result?.details;
  const riskSummary = details?.risk_summary;
  const headlines = details?.news_headlines ?? [];
  const finalSignal = summary?.final_signal ?? summary?.base_signal ?? "N/A";

  return (
    <PageShell>
      <section className="hero compact-hero">
        <p className="eyebrow">Ticker analysis</p>
        <h1>Analyze one ticker through the Meroq API.</h1>
        <p>Use the lightweight frontend to call the same local analysis engine behind Streamlit.</p>
      </section>

      <div className="grid cols-2 align-start">
        <form className="card form" onSubmit={onSubmit}>
          <label>
            Ticker
            <input value={ticker} onChange={(event) => setTicker(event.target.value.toUpperCase())} />
          </label>
          <div className="grid cols-2">
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
          </div>
          <label className="checkbox-row">
            <input type="checkbox" checked={includeNews} onChange={(event) => setIncludeNews(event.target.checked)} />
            Include recent news sentiment
          </label>
          <label className="checkbox-row">
            <input type="checkbox" checked={includeRisk} onChange={(event) => setIncludeRisk(event.target.checked)} />
            Include Monte Carlo risk lens
          </label>
          <button disabled={loading}>{loading ? "Running..." : "Run analysis"}</button>
        </form>

        <section className="card">
          <div className="card-heading-row">
            <div>
              <p className="status-label">Current result</p>
              <h2>{summary ? `${String(summary.ticker)} outlook` : "Waiting for analysis"}</h2>
            </div>
            {summary ? <StatusPill label={String(finalSignal)} tone={signalTone(finalSignal)} /> : null}
          </div>
          {!summary && !error && !loading ? <p className="muted">Submit a ticker to see a concise signal and risk summary.</p> : null}
          {loading ? <LoadingState label="Running ticker analysis..." /> : null}
          {error ? <ErrorBox message={error} /> : null}
          {summary ? (
            <div className="result-stack">
              <ProbabilityBar value={summary.final_up_probability ?? summary.base_up_probability} label="Final up probability" />
              <p className="plain-summary">
                Meroq estimates a <strong>{String(finalSignal)}</strong> setup for {String(summary.ticker)}. The base model probability is{" "}
                <strong>{formatPct(summary.base_up_probability)}</strong>
                {summary.sentiment_adjustment_pct_points !== null && summary.sentiment_adjustment_pct_points !== undefined
                  ? `, with sentiment adjusting the final probability by ${formatSignedPctPoints(summary.sentiment_adjustment_pct_points)}`
                  : ""}
                .
              </p>
            </div>
          ) : null}
        </section>
      </div>

      {summary ? (
        <>
          <section className="grid cols-4" style={{ marginTop: 18 }}>
            <MetricCard label="Latest close" value={formatMoney(summary.latest_close)} helper={String(summary.latest_data_date ?? "")} />
            <MetricCard label="Base probability" value={formatPct(summary.base_up_probability)} />
            <MetricCard label="Adjusted probability" value={formatPct(summary.final_up_probability)} />
            <MetricCard label="News sentiment" value={String(summary.news_sentiment_label ?? "Skipped")} />
          </section>

          <section className="grid cols-3" style={{ marginTop: 18 }}>
            <MetricCard label="Risk profile" value={String(summary.risk_label ?? "Skipped")} />
            <MetricCard label="Positive return probability" value={formatPct(riskSummary?.probability_positive_return)} />
            <MetricCard label="Loss > 5% probability" value={formatPct(riskSummary?.probability_loss_gt_5pct)} />
          </section>

          <section className="card" style={{ marginTop: 18 }}>
            <h2>Recent headlines used</h2>
            {headlines.length ? (
              <ul className="headline-list">
                {headlines.slice(0, 5).map((row, index) => (
                  <li key={`${row.title ?? "headline"}-${index}`}>
                    <span>{String(row.title ?? "Untitled headline")}</span>
                    <small>{String(row.source ?? row.publisher ?? "news")}</small>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">No headline details returned. Enable news sentiment or request details from the API.</p>
            )}
          </section>
        </>
      ) : null}
    </PageShell>
  );
}
