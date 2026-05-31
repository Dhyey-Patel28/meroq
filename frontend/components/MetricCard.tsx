import type { ReactNode } from "react";

type MetricCardProps = {
  label: string;
  value: ReactNode;
  helper?: ReactNode;
  tone?: "neutral" | "positive" | "negative" | "warning";
};

export function MetricCard({ label, value, helper, tone = "neutral" }: MetricCardProps) {
  return (
    <section className={`metric-card tone-${tone}`}>
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value ?? "N/A"}</p>
      {helper ? <p className="metric-helper">{helper}</p> : null}
    </section>
  );
}
