type ProbabilityBarProps = {
  value: unknown;
  label?: string;
};

export function ProbabilityBar({ value, label = "Up probability" }: ProbabilityBarProps) {
  const number = Number(value);
  const clamped = Number.isFinite(number) ? Math.min(1, Math.max(0, number)) : 0;
  const percent = Math.round(clamped * 1000) / 10;

  return (
    <div className="probability-block">
      <div className="probability-label">
        <span>{label}</span>
        <strong>{Number.isFinite(number) ? `${percent.toFixed(1)}%` : "N/A"}</strong>
      </div>
      <div className="probability-track" aria-hidden="true">
        <div className="probability-fill" style={{ width: `${percent}%` }} />
      </div>
      <div className="probability-scale">
        <span>Bearish</span>
        <span>Neutral</span>
        <span>Bullish</span>
      </div>
    </div>
  );
}
