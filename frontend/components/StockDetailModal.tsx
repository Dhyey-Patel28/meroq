"use client";

import { useEffect, useState } from "react";
import { GradeBadge } from "@/components/GradeBadge";
import { NewsCard } from "@/components/NewsCard";
import { ProbabilityBar } from "@/components/ProbabilityBar";
import { StatusPill } from "@/components/StatusPill";
import { ErrorBox, LoadingState } from "@/components/StateBlocks";
import {
  analyzeTicker,
  formatMoney,
  formatNumber,
  formatPct,
  type ApiRecord,
  type TickerAnalysisResponse,
} from "@/lib/api";

function toneFromText(value: unknown): "neutral" | "positive" | "negative" | "warning" {
  const text = String(value ?? "").toLowerCase();
  if (text.includes("bullish") || text.includes("positive") || text.includes("constructive") || text.includes("low")) return "positive";
  if (text.includes("bearish") || text.includes("negative") || text.includes("elevated") || text.includes("high")) return "negative";
  if (text.includes("neutral") || text.includes("balanced") || text.includes("cautious")) return "warning";
  return "neutral";
}

function plainRead(summary: ApiRecord | null, risk: ApiRecord | undefined) {
  if (!summary) return "";
  const signal = String(summary.final_signal ?? summary.base_signal ?? "Neutral");
  const sentiment = String(summary.sentiment_label ?? "Mixed");
  const riskLabel = String(risk?.risk_label ?? summary.risk_label ?? "Balanced risk profile");
  return `${String(summary.ticker ?? "This ticker")} currently reads as ${signal.toLowerCase()}, with ${sentiment.toLowerCase()} sentiment and a ${riskLabel.toLowerCase()}.`;
}

export function StockDetailModal({
  ticker,
  period,
  baseRow,
  onClose,
}: {
  ticker: string | null;
  period: string;
  baseRow?: ApiRecord | null;
  onClose: () => void;
}) {
  const [result, setResult] = useState<TickerAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ticker) return;

    function onKeydown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    window.addEventListener("keydown", onKeydown);
    return () => window.removeEventListener("keydown", onKeydown);
  }, [onClose, ticker]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!ticker) return;
      if (String(baseRow?.status ?? "").toLowerCase() === "failed") {
        setResult(null);
        setError(String(baseRow?.error ?? `Unable to load ${ticker}.`));
        return;
      }
      setLoading(true);
      setError("");
      setResult(null);
      try {
        const response = await analyzeTicker({
          ticker,
          period,
          interval: "1d",
          model_name: "xgboost",
          include_risk: true,
          include_news: true,
          include_sentiment_fusion: true,
          news_source: "all_configured",
          sentiment_engine: "lightweight",
          max_news_items: 8,
          news_lookback_days: 14,
          simulation_horizon: 30,
          simulation_paths: 300,
          return_details: true,
        });
        if (!cancelled) setResult(response);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : `Unable to load details for ${ticker}.`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [baseRow, period, ticker]);

  if (!ticker) return null;

  const summary = result?.summary ?? baseRow ?? null;
  const details = result?.details;
  const headlines = details?.news_headlines ?? [];
  const riskSummary = details?.risk_summary;

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div className="modal-panel" onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true" aria-label={`${ticker} details`}>
        <button className="modal-close" type="button" onClick={onClose} aria-label="Close details">
          ×
        </button>

        <div className="card-heading-row" style={{ alignItems: "flex-start" }}>
          <div>
            <p className="status-label">Ticker detail</p>
            <h2 style={{ marginTop: 0 }}>{ticker}</h2>
            <p className="muted small">Click outside the panel or press Esc to close.</p>
          </div>
          {summary ? (
            <div className="badge-row">
              <GradeBadge grade={summary.meroq_grade} label={summary.meroq_grade_label} compact />
              {summary.final_signal ? <StatusPill label={String(summary.final_signal)} tone={toneFromText(summary.final_signal)} /> : null}
            </div>
          ) : null}
        </div>

        {loading ? <LoadingState label={`Loading ${ticker}…`} /> : null}
        {error ? <ErrorBox message={error} /> : null}

        {summary && !loading && !error ? (
          <div className="modal-stack">
            <div className="grid cols-4">
              <section className="metric-card">
                <p className="metric-label">Latest close</p>
                <p className="metric-value">{formatMoney(summary.latest_close)}</p>
              </section>
              <section className="metric-card">
                <p className="metric-label">Up probability</p>
                <p className="metric-value">{formatPct(summary.final_up_probability ?? summary.base_up_probability)}</p>
              </section>
              <section className="metric-card">
                <p className="metric-label">Meroq Grade</p>
                <p className="metric-value"><GradeBadge grade={summary.meroq_grade ?? baseRow?.meroq_grade} label={summary.meroq_grade_label ?? baseRow?.meroq_grade_label} /></p>
              </section>
              <section className="metric-card">
                <p className="metric-label">Risk read</p>
                <p className="metric-value" style={{ fontSize: "1.2rem" }}>{String(summary.risk_label ?? riskSummary?.risk_label ?? "N/A")}</p>
              </section>
            </div>

            <ProbabilityBar value={summary.final_up_probability ?? summary.base_up_probability} label="Current model read" />

            <section className="card subtle-card">
              <p className="status-label">Plain-English read</p>
              <p className="plain-summary">{plainRead(summary, riskSummary)}</p>
            </section>

            <section className="card grade-breakdown-card">
              <p className="status-label">Grade breakdown</p>
              <div className="grade-component-grid">
                <span><GradeBadge grade={summary.momentum_grade} compact /> Momentum</span>
                <span><GradeBadge grade={summary.risk_grade} compact /> Risk</span>
                <span><GradeBadge grade={summary.sentiment_grade} compact /> Sentiment</span>
                <span><GradeBadge grade={summary.model_confidence_grade} compact /> Model confidence</span>
              </div>
            </section>

            <div className="grid cols-3 align-start">
              <section className="card">
                <p className="status-label">Signal</p>
                <h3>{String(summary.final_signal ?? summary.base_signal ?? "N/A")}</h3>
                <p className="muted small">Base signal {String(summary.base_signal ?? "N/A")}</p>
              </section>
              <section className="card">
                <p className="status-label">Sentiment</p>
                <h3>{String(summary.sentiment_label ?? details?.sentiment_summary?.overall_label ?? "N/A")}</h3>
                <p className="muted small">Average score {formatNumber(summary.sentiment_score ?? details?.sentiment_summary?.average_score, 2)}</p>
              </section>
              <section className="card">
                <p className="status-label">Model quality</p>
                <h3>{formatPct(summary.model_accuracy, 1)}</h3>
                <p className="muted small">ROC AUC {formatNumber(summary.model_roc_auc, 2)}</p>
              </section>
            </div>

            <section className="card">
              <div className="card-heading-row">
                <h3>Recent source articles</h3>
                <span className="muted small">{headlines.length} headlines</span>
              </div>
              {headlines.length ? (
                <div className="headline-grid">
                  {headlines.map((headline, index) => (
                    <NewsCard key={`${headline.title ?? ticker}-${index}`} row={headline} />
                  ))}
                </div>
              ) : (
                <p className="muted">No source-linked headlines were returned for this ticker.</p>
              )}
            </section>
          </div>
        ) : null}
      </div>
    </div>
  );
}
