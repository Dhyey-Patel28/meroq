"use client";

import { FormEvent, useMemo, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { DonutChart } from "@/components/DonutChart";
import { GradeBadge } from "@/components/GradeBadge";
import { ErrorBox, LoadingState } from "@/components/StateBlocks";
import { MetricCard } from "@/components/MetricCard";
import { PageShell } from "@/components/PageShell";
import { StockDetailModal } from "@/components/StockDetailModal";
import { StatusPill } from "@/components/StatusPill";
import { analyzePortfolio, formatNumber, formatPct, formatSignedPctPoints, parseTickerList, type ApiRecord } from "@/lib/api";

const holdingColumns = [
  "ticker",
  "weight",
  "latest_close",
  "final_signal",
  "final_up_probability",
  "meroq_grade",
  "risk_label",
  "risk_loss_gt_5pct",
  "downside_contribution_share",
  "research_weight_delta",
  "allocation_review",
  "meroq_score",
  "exposure_note",
];

function asRecordArray(value: unknown): ApiRecord[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is ApiRecord => Boolean(item) && typeof item === "object" && !Array.isArray(item));
}

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

function buildGradeSlices(distribution: ApiRecord[]) {
  const colors: Record<string, string> = {
    A: "#047857",
    B: "#16a34a",
    C: "#f59e0b",
    D: "#d97706",
    F: "#dc2626",
    "N/A": "#94a3b8",
  };
  return distribution.map((row) => ({
    label: `Grade ${String(row.grade ?? "N/A")}`,
    value: Number(row.weight ?? 0),
    color: colors[String(row.grade ?? "N/A")] ?? "#94a3b8",
    helper: `${String(row.count ?? 0)} holdings`,
  }));
}

function toneForSeverity(value: unknown): "neutral" | "positive" | "negative" | "warning" {
  const text = String(value ?? "").toLowerCase();
  if (text.includes("positive")) return "positive";
  if (text.includes("negative")) return "negative";
  if (text.includes("warning")) return "warning";
  return "neutral";
}

function commandMetric(value: unknown, fallback = "N/A") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function contributionCopy(row: ApiRecord | undefined, metric: "risk" | "score") {
  if (!row) return "No contributor available yet.";
  if (metric === "risk") {
    return `${String(row.ticker)} drives ${formatPct(row.downside_contribution_share)} of weighted downside probability.`;
  }
  return `${String(row.ticker)} contributes ${formatNumber(row.weighted_meroq_score)} weighted Meroq points.`;
}

function signedNumber(value: unknown, decimals = 1) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "N/A";
  return `${number >= 0 ? "+" : ""}${number.toFixed(decimals)}`;
}

function deltaTone(value: unknown): "neutral" | "positive" | "negative" | "warning" {
  const number = Number(value);
  if (!Number.isFinite(number) || Math.abs(number) < 0.0005) return "neutral";
  return number > 0 ? "positive" : "warning";
}

function ScenarioCard({ scenario }: { scenario: ApiRecord }) {
  const isCurrent = scenario.scenario_key === "current";
  return (
    <article className={`scenario-card ${isCurrent ? "is-current" : ""}`}>
      <div className="card-heading-row">
        <div>
          <p className="status-label">Scenario</p>
          <h3>{String(scenario.label ?? "Portfolio scenario")}</h3>
        </div>
        <GradeBadge grade={scenario.portfolio_grade} label={scenario.portfolio_grade_label} compact />
      </div>
      <p className="muted small scenario-description">{String(scenario.description ?? "Transparent what-if view based on current holdings.")}</p>
      <div className="scenario-metrics">
        <div>
          <span>Score</span>
          <strong>{formatNumber(scenario.weighted_meroq_score)}</strong>
          {!isCurrent ? <em className={`delta-pill tone-${deltaTone(scenario.score_delta)}`}>{signedNumber(scenario.score_delta)} pts</em> : null}
        </div>
        <div>
          <span>Downside</span>
          <strong>{formatPct(scenario.weighted_downside_probability)}</strong>
          {!isCurrent ? <em className={`delta-pill tone-${deltaTone(Number(scenario.downside_delta) * -1)}`}>{formatSignedPctPoints(scenario.downside_delta)}</em> : null}
        </div>
        <div>
          <span>Up prob.</span>
          <strong>{formatPct(scenario.weighted_up_probability)}</strong>
          {!isCurrent ? <em className={`delta-pill tone-${deltaTone(scenario.up_probability_delta)}`}>{formatSignedPctPoints(scenario.up_probability_delta)}</em> : null}
        </div>
      </div>
      <p className="muted small scenario-summary">{String(scenario.summary ?? "Run a scan to compare this scenario.")}</p>
    </article>
  );
}


function InsightCard({ alert }: { alert: ApiRecord }) {
  const tone = toneForSeverity(alert.severity);
  return (
    <section className={`insight-card tone-${tone}`}>
      <div className="card-heading-row">
        <div>
          <p className="status-label">Command insight</p>
          <h3>{String(alert.title ?? "Portfolio insight")}</h3>
        </div>
        {alert.ticker ? <StatusPill label={String(alert.ticker)} tone={tone} /> : null}
      </div>
      <p className="muted">{String(alert.detail ?? "Review this exposure before relying on the aggregate portfolio read.")}</p>
    </section>
  );
}

function ContributorList({ title, rows, metric }: { title: string; rows: ApiRecord[]; metric: "risk" | "score" | "weak" | "shift" }) {
  return (
    <section className="card contributor-card">
      <div className="card-heading-row">
        <h3>{title}</h3>
        <span className="muted small">Top {rows.length || 0}</span>
      </div>
      {rows.length ? (
        <div className="contributor-list">
          {rows.map((row) => (
            <div className="contributor-row" key={`${title}-${String(row.ticker)}`}>
              <div>
                <strong>{String(row.ticker)}</strong>
                <p className="muted small">{String(row.allocation_review ?? row.exposure_note ?? row.risk_label ?? "Portfolio contributor")}</p>
              </div>
              <div className="contributor-metric">
                {metric === "risk"
                  ? formatPct(row.downside_contribution_share)
                  : metric === "score"
                    ? formatNumber(row.weighted_meroq_score)
                    : metric === "shift"
                      ? formatSignedPctPoints(row.research_weight_delta)
                      : formatNumber(row.meroq_score)}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">Run an analysis to populate this list.</p>
      )}
    </section>
  );
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
  const alerts = useMemo(() => asRecordArray(summary?.portfolio_alerts), [summary]);
  const gradeDistribution = useMemo(() => asRecordArray(summary?.grade_distribution), [summary]);
  const gradeSlices = useMemo(() => buildGradeSlices(gradeDistribution), [gradeDistribution]);
  const topRiskContributors = useMemo(() => asRecordArray(summary?.top_risk_contributors), [summary]);
  const topScoreContributors = useMemo(() => asRecordArray(summary?.top_score_contributors), [summary]);
  const weakestHoldings = useMemo(() => asRecordArray(summary?.weakest_holdings), [summary]);
  const scenarioComparison = useMemo(() => asRecordArray(summary?.scenario_comparison), [summary]);
  const researchAdds = useMemo(() => asRecordArray(summary?.research_adds), [summary]);
  const researchTrims = useMemo(() => asRecordArray(summary?.research_trims), [summary]);
  const bullishWeight = Number(summary?.bullish_weight ?? 0);
  const bearishWeight = Number(summary?.bearish_weight ?? 0);
  const neutralWeight = Math.max(0, 1 - bullishWeight - bearishWeight);
  const highRiskWeight = Number(summary?.high_risk_weight ?? 0);
  const topRisk = topRiskContributors[0];
  const topScore = topScoreContributors[0];
  const weakest = weakestHoldings[0];

  return (
    <PageShell>
      <section className="hero compact-hero">
        <p className="eyebrow">Portfolio command center</p>
        <h1>See what is carrying the portfolio read.</h1>
        <p>Use custom weights to expose concentration, downside drivers, weak setups, and grade distribution before drilling into a holding.</p>
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
          <section className="grid cols-4 portfolio-command-grid" style={{ marginTop: 18 }}>
            <MetricCard label="Holdings" value={String(summary.holding_count ?? holdings.length)} helper="Scanned successfully" />
            <MetricCard label="Portfolio grade" value={<GradeBadge grade={summary.portfolio_grade} label={summary.portfolio_grade_label} />} helper={String(summary.portfolio_grade_label ?? "Research grade, not advice.")} />
            <MetricCard label="Weighted Meroq score" value={formatNumber(summary.weighted_meroq_score)} helper={commandMetric(summary.portfolio_health_label)} />
            <MetricCard label="Weighted up probability" value={formatPct(summary.weighted_up_probability)} helper={String(summary.portfolio_signal_label ?? "Signal profile")} />
            <MetricCard label="Downside exposure" value={formatPct(summary.weighted_downside_probability)} helper={`High-risk weight ${formatPct(highRiskWeight)}`} tone="warning" />
            <MetricCard label="Concentration" value={commandMetric(summary.concentration_label)} helper={`${String(summary.largest_position_ticker ?? "Top holding")} at ${formatPct(summary.largest_position_weight)}`} tone={String(summary.concentration_label) === "Concentrated" ? "warning" : "neutral"} />
            <MetricCard label="Top risk driver" value={String(topRisk?.ticker ?? "N/A")} helper={contributionCopy(topRisk, "risk")} tone="warning" />
            <MetricCard label="Weakest setup" value={String(weakest?.ticker ?? "N/A")} helper={weakest ? `Meroq Score ${formatNumber(weakest.meroq_score)}` : "No weak holding available"} tone={Number(weakest?.meroq_score ?? 100) < 42 ? "negative" : "neutral"} />
          </section>

          <section className="card callout-card" style={{ marginTop: 18 }}>
            <div className="card-heading-row">
              <div>
                <p className="status-label">Portfolio read</p>
                <h2>{String(summary.portfolio_signal_label ?? "Portfolio read")}</h2>
              </div>
              <StatusPill label={String(summary.portfolio_risk_label ?? "Risk read")} tone={highRiskWeight >= 0.35 ? "negative" : "warning"} />
            </div>
            <p className="plain-summary">{sentence}</p>
          </section>

          {scenarioComparison.length ? (
            <section className="card scenario-lab" style={{ marginTop: 18 }}>
              <div className="card-heading-row">
                <div>
                  <p className="status-label">Scenario lab</p>
                  <h2>Compare current, equal-weight, and research-weighted views.</h2>
                </div>
                <StatusPill label="What-if only" tone="neutral" />
              </div>
              <p className="muted small">{String(summary.scenario_disclaimer ?? "Scenario weights are diagnostic what-if views, not allocation advice.")}</p>
              <div className="scenario-grid">
                {scenarioComparison.map((scenario) => (
                  <ScenarioCard scenario={scenario} key={String(scenario.scenario_key ?? scenario.label)} />
                ))}
              </div>
              <div className="scenario-action-grid">
                <ContributorList title="Scenario adds" rows={researchAdds} metric="shift" />
                <ContributorList title="Scenario trims" rows={researchTrims} metric="shift" />
              </div>
            </section>
          ) : null}

          {alerts.length ? (
            <section className="insight-grid" style={{ marginTop: 18 }}>
              {alerts.map((alert, index) => (
                <InsightCard alert={alert} key={`${String(alert.title ?? "alert")}-${index}`} />
              ))}
            </section>
          ) : null}

          <section className="grid cols-3 align-start portfolio-chart-grid" style={{ marginTop: 18 }}>
            <DonutChart
              title="Holding weights"
              subtitle="Top allocations by current portfolio weights"
              centerLabel="Total"
              centerValue={formatPct(summary.total_weight)}
              slices={allocationSlices}
            />
            <DonutChart
              title="Signal posture"
              subtitle="Weights rolled up from current holdings"
              centerLabel="High risk"
              centerValue={formatPct(highRiskWeight)}
              slices={[
                { label: "Bullish weight", value: bullishWeight, color: "#16a34a", helper: "Signal share" },
                { label: "Neutral weight", value: neutralWeight, color: "#f59e0b", helper: "Middle ground" },
                { label: "Bearish weight", value: bearishWeight, color: "#dc2626", helper: "Defensive share" },
              ]}
            />
            <DonutChart
              title="Grade exposure"
              subtitle="Portfolio weight by Meroq Grade"
              centerLabel="Grade"
              centerValue={String(summary.portfolio_grade ?? "N/A")}
              slices={gradeSlices.length ? gradeSlices : [{ label: "Unrated", value: 1, color: "#94a3b8" }]}
            />
          </section>

          <section className="grid cols-3 align-start" style={{ marginTop: 18 }}>
            <ContributorList title="Score contributors" rows={topScoreContributors} metric="score" />
            <ContributorList title="Downside contributors" rows={topRiskContributors} metric="risk" />
            <ContributorList title="Weakest holdings" rows={weakestHoldings} metric="weak" />
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
          searchPlaceholder="Search holdings, weights, signals, risk, or exposure notes…"
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
