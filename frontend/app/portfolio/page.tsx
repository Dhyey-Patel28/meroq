"use client";

import { FormEvent, useMemo, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { DonutChart } from "@/components/DonutChart";
import { GradeBadge } from "@/components/GradeBadge";
import { ErrorBox, LoadingState } from "@/components/StateBlocks";
import { MetricCard } from "@/components/MetricCard";
import { PageShell } from "@/components/PageShell";
import { StockDetailModal } from "@/components/StockDetailModal";
import { analyzePortfolio, formatNumber, formatPct, parseTickerList, type ApiRecord } from "@/lib/api";

const holdingColumns = [
  "ticker",
  "weight",
  "latest_close",
  "final_signal",
  "final_up_probability",
  "meroq_grade",
  "risk_label",
  "risk_loss_gt_5pct",
  "meroq_score",
];

function buildAllocationSlices(holdings: ApiRecord[]) {
  const top = holdings.slice(0, 5).map((row, index) => ({
    label: String(row.ticker),
    value: Number(row.weight ?? 0),
    color: ["#3346d3", "#5b6cf0", "#6f86ff", "#90a3ff", "#b0bcff"][index] ?? "#d5ddff",
  }));
  const remainder = holdings.slice(5).reduce((sum, row) => sum + Number(row.weight ?? 0), 0);
  if (remainder > 0) top.push({ label: "Other holdings", value: remainder, color: "#d9e0ee" });
  return top;
}

export default function PortfolioPage() {
  const [tickers, setTickers] = useState("MSTR,COIN,HOOD,SOFI,PYPL,SQ,V,MA,MARA");
  const [weights, setWeights] = useState("MSTR:20,COIN:17,HOOD:15,SOFI:13,PYPL:11,SQ:9,V:7,MA:5,MARA:3");
  const [holdings, setHoldings] = useState<ApiRecord[]>([]);
  const [summary, setSummary] = useState<ApiRecord | null>(null);
  const [sentence, setSentence] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedRow, setSelectedRow] = useState<ApiRecord | null>(null);

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

  const allocationSlices = useMemo(() => buildAllocationSlices(holdings), [holdings]);
  const bullishWeight = Number(summary?.bullish_weight ?? 0);
  const bearishWeight = Number(summary?.bearish_weight ?? 0);
  const neutralWeight = Math.max(0, 1 - bullishWeight - bearishWeight);
  const highRiskWeight = Number(summary?.high_risk_weight ?? 0);

  return (
    <PageShell>
      <section className="hero compact-hero">
        <p className="eyebrow">Portfolio view</p>
        <h1>Turn watchlist signals into weighted exposure.</h1>
        <p>Use custom weights to see which positions drive score, probability, and downside risk — then click into any holding.</p>
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
        <div className="button-row">
          <button disabled={loading}>{loading ? "Analyzing…" : "Analyze portfolio"}</button>
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setTickers("MSTR,COIN,HOOD,SOFI,PYPL,SQ,V,MA,MARA");
              setWeights("MSTR:20,COIN:17,HOOD:15,SOFI:13,PYPL:11,SQ:9,V:7,MA:5,MARA:3");
              setHoldings([]);
              setSummary(null);
              setSentence("");
              setError("");
            }}
          >
            Reset
          </button>
        </div>
      </form>

      {loading ? <LoadingState label="Analyzing portfolio…" /> : null}
      {error ? <ErrorBox message={error} /> : null}

      {summary ? (
        <>
          <section className="grid cols-4" style={{ marginTop: 18 }}>
            <MetricCard label="Holdings" value={String(summary.holding_count ?? holdings.length)} />
            <MetricCard label="Portfolio grade" value={<GradeBadge grade={summary.portfolio_grade} label={summary.portfolio_grade_label} />} helper={String(summary.portfolio_grade_label ?? "Research grade, not advice.")} />
            <MetricCard label="Weighted Meroq score" value={formatNumber(summary.weighted_meroq_score)} />
            <MetricCard label="Weighted up probability" value={formatPct(summary.weighted_up_probability)} />
            <MetricCard label="Downside exposure" value={formatPct(summary.weighted_downside_probability)} tone="warning" />
          </section>

          <section className="card callout-card" style={{ marginTop: 18 }}>
            <p className="status-label">Portfolio read</p>
            <h2>{String(summary.portfolio_signal_label ?? "Portfolio read")}</h2>
            <p className="plain-summary">{sentence}</p>
          </section>

          <section className="grid cols-2" style={{ marginTop: 18 }}>
            <DonutChart
              title="Holding weights"
              subtitle="Top allocations by current portfolio weights"
              centerLabel="Total"
              centerValue={formatPct(summary.total_weight)}
              slices={allocationSlices}
            />
            <DonutChart
              title="Signal and risk posture"
              subtitle="Weights rolled up from the current portfolio summary"
              centerLabel="High risk"
              centerValue={formatPct(highRiskWeight)}
              slices={[
                { label: "Bullish weight", value: bullishWeight, color: "#16a34a", helper: "Signal share" },
                { label: "Neutral weight", value: neutralWeight, color: "#f59e0b", helper: "Middle ground" },
                { label: "Bearish weight", value: bearishWeight, color: "#dc2626", helper: "Defensive share" },
              ]}
            />
          </section>
        </>
      ) : null}

      <section className="card" style={{ marginTop: 18 }}>
        <div className="card-heading-row">
          <div>
            <h2>Holdings</h2>
            <p className="muted small">Search the table or click any row for a modal with deeper ticker context.</p>
          </div>
          {holdings.length ? <span className="muted small">Sorted by portfolio weight</span> : null}
        </div>
        <DataTable
          rows={holdings}
          columns={holdingColumns}
          searchPlaceholder="Search holdings, weights, signals, or risk…"
          onRowClick={(row) => setSelectedRow(row)}
          rowHint="Holding details"
          exportFilename="meroq-portfolio-holdings.csv"
          legend={
            <div className="legend-row">
              <span className="legend-pill positive">▲ Constructive / lower concern</span>
              <span className="legend-pill warning">● Neutral / balanced</span>
              <span className="legend-pill negative">▼ Cautious / higher concern</span>
            </div>
          }
        />
      </section>

      <StockDetailModal ticker={selectedRow ? String(selectedRow.ticker ?? "") : null} period="5y" baseRow={selectedRow} onClose={() => setSelectedRow(null)} />
    </PageShell>
  );
}
