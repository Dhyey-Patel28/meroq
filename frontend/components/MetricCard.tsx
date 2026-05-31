import type { ReactNode } from "react";
import { InfoTip } from "@/components/InfoTip";

type MetricCardProps = {
  label: string;
  value: ReactNode;
  helper?: ReactNode;
  info?: string;
  tone?: "neutral" | "positive" | "negative" | "warning";
};

export function MetricCard({ label, value, helper, info, tone = "neutral" }: MetricCardProps) {
  return (
    <section className={`metric-card tone-${tone}`}>
      <p className="metric-label">
        {label}
        {info ? <InfoTip label={label}>{info}</InfoTip> : null}
      </p>
      <p className="metric-value">{value ?? "N/A"}</p>
      {helper ? <p className="metric-helper">{helper}</p> : null}
    </section>
  );
}
