import { formatPct } from "@/lib/api";

type Slice = {
  label: string;
  value: number;
  color: string;
  helper?: string;
};

const RADIUS = 58;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function DonutChart({
  title,
  subtitle,
  centerLabel,
  centerValue,
  slices,
}: {
  title: string;
  subtitle?: string;
  centerLabel: string;
  centerValue: string;
  slices: Slice[];
}) {
  const total = slices.reduce((sum, slice) => sum + Math.max(0, slice.value), 0);
  let offset = 0;

  return (
    <section className="card chart-card">
      <div className="card-heading-row">
        <div>
          <h2>{title}</h2>
          {subtitle ? <p className="muted small">{subtitle}</p> : null}
        </div>
      </div>
      <div className="donut-layout">
        <div className="donut-shell" aria-hidden="true">
          <svg viewBox="0 0 160 160" className="donut-svg">
            <circle cx="80" cy="80" r={RADIUS} fill="none" stroke="#eef2f7" strokeWidth="20" />
            {slices.map((slice) => {
              const safeValue = Math.max(0, slice.value);
              const length = total > 0 ? (safeValue / total) * CIRCUMFERENCE : 0;
              const dasharray = `${length} ${Math.max(0, CIRCUMFERENCE - length)}`;
              const dashoffset = -offset;
              offset += length;
              return (
                <circle
                  key={slice.label}
                  cx="80"
                  cy="80"
                  r={RADIUS}
                  fill="none"
                  stroke={slice.color}
                  strokeWidth="20"
                  strokeLinecap="butt"
                  strokeDasharray={dasharray}
                  strokeDashoffset={dashoffset}
                  transform="rotate(-90 80 80)"
                />
              );
            })}
          </svg>
          <div className="donut-center">
            <span>{centerLabel}</span>
            <strong>{centerValue}</strong>
          </div>
        </div>
        <div className="donut-legend">
          {slices.map((slice) => (
            <div className="donut-legend-item" key={slice.label}>
              <span className="legend-swatch" style={{ backgroundColor: slice.color }} />
              <div>
                <strong>{slice.label}</strong>
                <div className="muted small">
                  {formatPct(slice.value, 1)}
                  {slice.helper ? ` · ${slice.helper}` : ""}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
