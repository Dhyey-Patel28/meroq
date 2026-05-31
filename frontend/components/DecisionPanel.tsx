import type { ApiRecord } from "@/lib/api";
import { formatPct } from "@/lib/api";

type DecisionPanelProps = {
  summary: ApiRecord;
  riskSummary?: ApiRecord;
};

function probabilityText(value: unknown) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "unknown";
  if (number >= 0.55) return "leans upward";
  if (number <= 0.45) return "leans downward";
  return "is close to balanced";
}

export function DecisionPanel({ summary, riskSummary }: DecisionPanelProps) {
  const finalProbability = summary.final_up_probability ?? summary.base_up_probability;
  const sentiment = String(summary.news_sentiment_label ?? "not available").toLowerCase();
  const risk = String(summary.risk_label ?? "risk unavailable").toLowerCase();
  const downside = riskSummary?.probability_loss_gt_5pct;

  return (
    <section className="decision-panel">
      <div>
        <p className="status-label">Decision read</p>
        <h2>What Meroq is saying</h2>
      </div>
      <div className="decision-grid">
        <article>
          <span>Direction</span>
          <strong>{probabilityText(finalProbability)}</strong>
          <p>The adjusted probability is {formatPct(finalProbability)}.</p>
        </article>
        <article>
          <span>Evidence</span>
          <strong>News tone is {sentiment}</strong>
          <p>Open the source articles before relying on the sentiment score.</p>
        </article>
        <article>
          <span>Risk</span>
          <strong>{risk}</strong>
          <p>Loss &gt; 5% probability: {formatPct(downside)}.</p>
        </article>
      </div>
    </section>
  );
}
