import { InfoTip } from "@/components/InfoTip";

function toneForGrade(grade: unknown) {
  const text = String(grade ?? "").toUpperCase();
  if (text === "A" || text === "B") return "positive";
  if (text === "C") return "warning";
  if (text === "D" || text === "F") return "negative";
  return "neutral";
}

export function GradeBadge({ grade, label, compact = false }: { grade: unknown; label?: unknown; compact?: boolean }) {
  const value = String(grade ?? "N/A").toUpperCase();
  const title = String(label ?? "Meroq Grade summarizes score, risk, sentiment, momentum, and model confidence. It is not financial advice.");
  return (
    <span className={`grade-badge tone-${toneForGrade(value)} ${compact ? "compact" : ""}`} title={title}>
      <strong>{value}</strong>
      {!compact ? <span>{title}</span> : null}
      {compact ? <InfoTip label="Meroq Grade">{title}</InfoTip> : null}
    </span>
  );
}
