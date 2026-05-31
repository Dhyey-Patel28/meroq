import type { ApiRecord } from "@/lib/api";
import { formatMoney, formatPct } from "@/lib/api";

type ForecastBandProps = {
  currentPrice: unknown;
  rows?: ApiRecord[];
  horizon?: unknown;
};

function numeric(value: unknown): number | null {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function pointsFor(rows: ApiRecord[], key: string, xScale: (step: number) => number, yScale: (price: number) => number) {
  return rows
    .map((row, index) => {
      const step = numeric(row.step) ?? index + 1;
      const price = numeric(row[key]);
      if (price === null) return null;
      return `${xScale(step)},${yScale(price)}`;
    })
    .filter(Boolean)
    .join(" ");
}

export function ForecastBand({ currentPrice, rows = [], horizon }: ForecastBandProps) {
  const usableRows = rows
    .map((row, index) => ({
      step: numeric(row.step) ?? index + 1,
      p10: numeric(row.p10),
      p50: numeric(row.p50),
      p90: numeric(row.p90),
    }))
    .filter((row) => row.p10 !== null && row.p50 !== null && row.p90 !== null) as Array<{
      step: number;
      p10: number;
      p50: number;
      p90: number;
    }>;

  const latest = numeric(currentPrice);

  if (!usableRows.length || latest === null) {
    return (
      <section className="forecast-empty">
        <p className="muted">Forecast range is unavailable for this run. Enable the risk simulation to create a future price range.</p>
      </section>
    );
  }

  const last = usableRows[usableRows.length - 1];
  const allPrices = [latest, ...usableRows.flatMap((row) => [row.p10, row.p50, row.p90])];
  const minPrice = Math.min(...allPrices);
  const maxPrice = Math.max(...allPrices);
  const padding = Math.max((maxPrice - minPrice) * 0.12, latest * 0.015);
  const yMin = minPrice - padding;
  const yMax = maxPrice + padding;
  const maxStep = Math.max(...usableRows.map((row) => row.step));

  const width = 760;
  const height = 300;
  const left = 56;
  const right = 24;
  const top = 26;
  const bottom = 46;
  const innerWidth = width - left - right;
  const innerHeight = height - top - bottom;

  const xScale = (step: number) => left + (step / maxStep) * innerWidth;
  const yScale = (price: number) => top + ((yMax - price) / (yMax - yMin)) * innerHeight;

  const p90Points = pointsFor(usableRows, "p90", xScale, yScale);
  const p50Points = pointsFor(usableRows, "p50", xScale, yScale);
  const p10Points = pointsFor([...usableRows].reverse(), "p10", xScale, yScale);
  const bandPolygon = `${p90Points} ${p10Points}`;
  const currentY = yScale(latest);
  const finalReturn = last.p50 / latest - 1;

  return (
    <section className="forecast-card">
      <div className="forecast-header">
        <div>
          <p className="status-label">Forecast range</p>
          <h2>Current close with likely future range</h2>
          <p className="muted">
            The shaded region is the 10th to 90th percentile simulation range. The center line is the median path.
          </p>
        </div>
        <div className="forecast-summary-pill">
          <span>Median ending price</span>
          <strong>{formatMoney(last.p50)}</strong>
          <small>{formatPct(finalReturn)} over {String(horizon ?? maxStep)} trading days</small>
        </div>
      </div>

      <div className="forecast-chart-wrap" role="img" aria-label="Forecast range chart showing current price, median path, and likely price range.">
        <svg viewBox={`0 0 ${width} ${height}`} className="forecast-svg">
          <line x1={left} y1={currentY} x2={width - right} y2={currentY} className="forecast-current-line" />
          <text x={left} y={currentY - 8} className="forecast-axis-text">
            Current {formatMoney(latest)}
          </text>

          <line x1={left} y1={top} x2={left} y2={height - bottom} className="forecast-axis" />
          <line x1={left} y1={height - bottom} x2={width - right} y2={height - bottom} className="forecast-axis" />

          <text x={left} y={height - 14} className="forecast-axis-text">Today</text>
          <text x={width - right - 90} y={height - 14} className="forecast-axis-text">+{String(horizon ?? maxStep)} trading days</text>
          <text x={left} y={top - 8} className="forecast-axis-text">{formatMoney(yMax)}</text>
          <text x={left} y={height - bottom + 18} className="forecast-axis-text">{formatMoney(yMin)}</text>

          <polygon points={bandPolygon} className="forecast-band" />
          <polyline points={pointsFor(usableRows, "p50", xScale, yScale)} className="forecast-median" />
          <polyline points={pointsFor(usableRows, "p90", xScale, yScale)} className="forecast-bound" />
          <polyline points={pointsFor(usableRows, "p10", xScale, yScale)} className="forecast-bound" />
          <circle cx={left} cy={currentY} r="5" className="forecast-dot" />
          <circle cx={xScale(last.step)} cy={yScale(last.p50)} r="5" className="forecast-dot forecast-dot-final" />
        </svg>
      </div>

      <div className="forecast-three-up">
        <div>
          <span>Downside range</span>
          <strong>{formatMoney(last.p10)}</strong>
        </div>
        <div>
          <span>Median path</span>
          <strong>{formatMoney(last.p50)}</strong>
        </div>
        <div>
          <span>Upside range</span>
          <strong>{formatMoney(last.p90)}</strong>
        </div>
      </div>
    </section>
  );
}
