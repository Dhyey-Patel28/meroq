"use client";

import { FormEvent, useMemo, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { DecisionPanel } from "@/components/DecisionPanel";
import { ErrorBox, LoadingState } from "@/components/StateBlocks";
import { ForecastBand } from "@/components/ForecastBand";
import { GradeBadge } from "@/components/GradeBadge";
import { MetricCard } from "@/components/MetricCard";
import { NewsCard } from "@/components/NewsCard";
import { PageShell } from "@/components/PageShell";
import { ProbabilityBar } from "@/components/ProbabilityBar";
import { StatusPill } from "@/components/StatusPill";
import { TrustPanel } from "@/components/TrustPanel";
import {
  analyzeTicker,
  formatMoney,
  formatNumber,
  formatPct,
  formatSignedPctPoints,
  type ApiRecord,
  type TickerAnalysisResponse,
} from "@/lib/api";

function signalTone(signal: unknown): "neutral" | "positive" | "negative" | "warning" {
  const text = String(signal ?? "").toLowerCase();
  if (text.includes("bull")) return "positive";
  if (text.includes("bear")) return "negative";
  if (text.includes("neutral")) return "warning";
  return "neutral";
}

function confidenceLabel(probability: unknown) {
  const p = Number(probability);
  if (!Number.isFinite(p)) return "Unknown";
  const distance = Math.abs(p - 0.5);
  if (distance >= 0.15) return "Higher";
  if (distance >= 0.07) return "Moderate";
  return "Low";
}

function headlineSourceSummary(headlines: ApiRecord[]) {
  const sources = Array.from(
    new Set(
      headlines
        .map((row) => String(row.source ?? row.publisher ?? "").trim())
        .filter(Boolean),
    ),
  );
  if (!sources.length) return "No source detail returned";
  return sources.slice(0, 4).join(", ");
}

function numeric(value: unknown) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function records(value: unknown): ApiRecord[] {
  return Array.isArray(value) ? (value.filter((item) => item && typeof item === "object") as ApiRecord[]) : [];
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)).filter(Boolean) : [];
}

function tone(value: unknown): "neutral" | "positive" | "negative" | "warning" {
  const text = String(value ?? "").toLowerCase();
  if (["positive", "success", "constructive"].some((token) => text.includes(token))) return "positive";
  if (["negative", "danger", "risk", "caution"].some((token) => text.includes(token))) return "negative";
  if (["warning", "partial", "balanced", "moderate", "low"].some((token) => text.includes(token))) return "warning";
  return "neutral";
}

function plainLanguageRead(summary: ApiRecord, riskSummary?: ApiRecord) {
  const finalProbability = numeric(summary.final_up_probability ?? summary.base_up_probability);
  const sentiment = String(summary.news_sentiment_label ?? "Skipped");
  const risk = String(summary.risk_label ?? "Risk unavailable");
  const confidence = confidenceLabel(finalProbability);

  if (finalProbability === null) {
    return "Meroq could not produce a probability for this run.";
  }

  const direction =
    finalProbability >= 0.55
      ? "leans constructive"
      : finalProbability <= 0.45
        ? "leans cautious"
        : "is close to balanced";

  const riskLoss = riskSummary?.probability_loss_gt_5pct;
  const riskClause = Number.isFinite(Number(riskLoss))
    ? ` The risk simulation estimates ${formatPct(riskLoss)} probability of a loss greater than 5% over the selected horizon.`
    : "";

  return `Meroq ${direction} with ${confidence.toLowerCase()} confidence. Recent news sentiment is ${sentiment.toLowerCase()}, and the current risk lens is ${risk.toLowerCase()}.${riskClause}`;
}

const headlineColumns = ["published_at", "publisher", "source", "target_relevance_label", "target_sentiment_label", "sentiment_score", "confidence", "reason_tags", "title", "url"];
const suggestedTickers = ["AAPL", "MSFT", "NVDA", "SPY", "HOG", "PLAY"];

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
  const brief = result?.brief;
  const details = result?.details;
  const riskSummary = details?.risk_summary;
  const riskPercentiles = details?.risk_percentiles ?? [];
  const headlines = details?.news_headlines ?? [];
  const finalSignal = summary?.final_signal ?? summary?.base_signal ?? "N/A";
  const confidence = confidenceLabel(summary?.final_up_probability ?? summary?.base_up_probability);
  const read = useMemo(() => (summary ? plainLanguageRead(summary, riskSummary) : ""), [summary, riskSummary]);
  const sourceSummary = headlineSourceSummary(headlines);
  const briefKeyPoints = records(brief?.key_points);
  const watchItems = strings(brief?.watch_items);
  const researchChecks = strings(brief?.research_checks);

  return (
    <PageShell>
      <section className="hero compact-hero product-hero-split">
        <div>
          <p className="eyebrow">Ticker analysis</p>
          <h1>Read the ticker like an analyst one-pager.</h1>
          <p>
            Run a local Meroq analysis for one ticker. The page now starts with stance, conviction, primary driver,
            key evidence, and research checks before exposing the raw model details.
          </p>
        </div>
        <div className="hero-mini-card">
          <span>Analyst brief flow</span>
          <strong>Stance → driver → checklist → evidence</strong>
        </div>
      </section>

      <div className="grid cols-2 align-start">
        <form className="card form" onSubmit={onSubmit}>
          <label>
            Ticker
            <input value={ticker} onChange={(event) => setTicker(event.target.value.toUpperCase())} />
          </label>
          <div className="ticker-chip-row" aria-label="Suggested tickers">
            {suggestedTickers.map((symbol) => (
              <button className="ticker-chip" type="button" key={symbol} onClick={() => setTicker(symbol)}>
                {symbol}
              </button>
            ))}
          </div>
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
          <p className="muted small">Meroq runs locally through your FastAPI backend. Results are research signals, not trading instructions.</p>
        </form>

        <section className="card result-card">
          <div className="card-heading-row">
            <div>
              <p className="status-label">Current read</p>
              <h2>{summary ? `${String(summary.ticker)} outlook` : "Waiting for analysis"}</h2>
            </div>
            {summary ? (
              <div className="badge-row">
                <GradeBadge grade={summary.meroq_grade} label={summary.meroq_grade_label} compact />
                <StatusPill label={String(finalSignal)} tone={signalTone(finalSignal)} />
              </div>
            ) : null}
          </div>
          {!summary && !error && !loading ? <p className="muted">Submit a ticker to see the concise signal, risk, and source-backed sentiment evidence.</p> : null}
          {loading ? <LoadingState label="Running ticker analysis..." /> : null}
          {error ? <ErrorBox message={error} /> : null}
          {summary ? (
            <div className="result-stack">
              <ProbabilityBar value={summary.final_up_probability ?? summary.base_up_probability} label="Final up probability" />
              <div className="insight-summary">
                <span className="status-label">Plain-English read</span>
                <p>{read}</p>
              </div>
            </div>
          ) : null}
        </section>
      </div>

      {summary && brief ? (
        <section className="card analyst-brief-card" style={{ marginTop: 18 }}>
          <div className="card-heading-row">
            <div>
              <p className="status-label">Analyst brief</p>
              <h2>{String(summary.ticker)} research read</h2>
            </div>
            <div className="badge-row">
              <StatusPill label={String(brief.stance_label ?? "Balanced / watch")} tone={tone(brief.stance_tone ?? brief.stance_label)} />
              <StatusPill label={String(brief.conviction_label ?? "Low conviction")} tone={tone(brief.conviction_tone ?? brief.conviction_label)} />
            </div>
          </div>

          <p className="analyst-brief-sentence">{String(brief.brief_sentence ?? read)}</p>

          <div className="analyst-driver-card">
            <span className="status-label">Primary driver</span>
            <strong>{String(brief.primary_driver ?? "No single dominant driver")}</strong>
          </div>

          {briefKeyPoints.length ? (
            <div className="brief-point-grid">
              {briefKeyPoints.map((point, index) => (
                <article className={`brief-point-card tone-${tone(point.tone)}`} key={`${point.title ?? "point"}-${index}`}>
                  <span>{String(point.title ?? "Evidence")}</span>
                  <strong>{String(point.value ?? "N/A")}</strong>
                  <p>{String(point.note ?? "")}</p>
                </article>
              ))}
            </div>
          ) : null}

          <div className="grid cols-2 analyst-check-grid">
            <div>
              <p className="status-label">Watch items</p>
              <ul className="checklist-list">
                {watchItems.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
            <div>
              <p className="status-label">Research checks</p>
              <ul className="checklist-list">
                {researchChecks.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          </div>
        </section>
      ) : null}

      {summary ? (
        <>
          <section className="grid cols-4" style={{ marginTop: 18 }}>
            <MetricCard label="Meroq Grade" value={<GradeBadge grade={summary.meroq_grade} label={summary.meroq_grade_label} />} helper={String(summary.grade_summary ?? "Research grade, not advice.")} />
            <MetricCard label="Latest close" value={formatMoney(summary.latest_close)} helper={String(summary.latest_data_date ?? "")} />
            <MetricCard label="Base probability" value={formatPct(summary.base_up_probability)} info="The model-only up probability before recent-news sentiment is applied." />
            <MetricCard label="Adjusted probability" value={formatPct(summary.final_up_probability)} info="The final probability after the conservative sentiment overlay. It is still a research estimate, not a guarantee." />
            <MetricCard label="Confidence" value={confidence} info="Based on how far the probability is from 50/50. Close-to-balanced forecasts are marked low confidence." />
          </section>

          <section className="grid cols-4" style={{ marginTop: 18 }}>
            <MetricCard label="News sentiment" value={String(summary.news_sentiment_label ?? "Skipped")} helper={sourceSummary} />
            <MetricCard label="Sentiment adjustment" value={formatSignedPctPoints(summary.sentiment_adjustment_pct_points)} info="How much recent-news sentiment tilted the model probability." />
            <MetricCard label="Positive return probability" value={formatPct(riskSummary?.probability_positive_return)} info="Monte Carlo estimate for ending above the current close over the selected horizon." />
            <MetricCard label="Loss > 5% probability" value={formatPct(riskSummary?.probability_loss_gt_5pct)} info="Monte Carlo estimate for a loss greater than 5% over the selected horizon." />
          </section>


          <section className="card grade-breakdown-card" style={{ marginTop: 18 }}>
            <div className="card-heading-row">
              <div>
                <p className="status-label">Meroq Grades</p>
                <h2>Component read</h2>
              </div>
              <GradeBadge grade={summary.meroq_grade} label={summary.meroq_grade_label} />
            </div>
            <p className="plain-summary">{String(summary.grade_summary ?? "Meroq Grade summarizes signal, risk, sentiment, momentum, and model confidence.")}</p>
            <div className="grade-component-grid">
              <span><GradeBadge grade={summary.momentum_grade} compact /> Momentum</span>
              <span><GradeBadge grade={summary.risk_grade} compact /> Risk</span>
              <span><GradeBadge grade={summary.sentiment_grade} compact /> Sentiment</span>
              <span><GradeBadge grade={summary.model_confidence_grade} compact /> Model confidence</span>
              <span><GradeBadge grade={summary.data_quality_grade} compact /> Data quality</span>
            </div>
          </section>

          <DecisionPanel summary={summary} riskSummary={riskSummary} />

          <ForecastBand
            currentPrice={summary.latest_close}
            rows={riskPercentiles}
            horizon={riskSummary?.horizon}
          />

          <TrustPanel />

          <section className="card" style={{ marginTop: 18 }}>
            <div className="card-heading-row">
              <div>
                <p className="status-label">Source-backed sentiment</p>
                <h2>Recent headlines used</h2>
              </div>
              {headlines.length ? <span className="muted small">{headlines.length} headlines returned</span> : null}
            </div>

            {headlines.length ? (
              <>
                <div className="news-grid">
                  {headlines.slice(0, 6).map((row, index) => (
                    <NewsCard row={row} key={`${row.url ?? row.title ?? "headline"}-${index}`} />
                  ))}
                </div>

                <details className="details-block">
                  <summary>View headline data table</summary>
                  <DataTable rows={headlines} columns={headlineColumns} maxRows={20} />
                </details>
              </>
            ) : (
              <p className="muted">No headline details returned. Enable news sentiment or request details from the API.</p>
            )}
          </section>

          <section className="card subtle-card" style={{ marginTop: 18 }}>
            <p className="status-label">Model context</p>
            <h2>Why the score should not be read alone</h2>
            <p className="muted">
              The model estimates direction probability, sentiment summarizes recent news tone, and risk simulation estimates a range of possible outcomes.
              A useful decision needs all three views together.
            </p>
            <div className="mini-grid">
              <span>Model probability: {formatPct(summary.base_up_probability)}</span>
              <span>Risk profile: {String(summary.risk_label ?? "Skipped")}</span>
              <span>Headlines: {formatNumber(summary.headlines_analyzed, 0)}</span>
            </div>
          </section>
        </>
      ) : null}
    </PageShell>
  );
}
