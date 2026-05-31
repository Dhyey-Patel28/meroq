type StatusPillProps = {
  label: string;
  tone?: "neutral" | "positive" | "negative" | "warning";
};

export function StatusPill({ label, tone = "neutral" }: StatusPillProps) {
  return <span className={`status-pill tone-${tone}`}>{label}</span>;
}
