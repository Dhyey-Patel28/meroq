type MetricCardProps = {
  label: string;
  value: string | number | null | undefined;
  helper?: string;
};

export function MetricCard({ label, value, helper }: MetricCardProps) {
  return (
    <section className="metric-card">
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value ?? "N/A"}</p>
      {helper ? <p className="metric-helper">{helper}</p> : null}
    </section>
  );
}
