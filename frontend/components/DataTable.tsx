import type { ApiRecord } from "@/lib/api";

function formatCell(value: ApiRecord[keyof ApiRecord]) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") {
    if (Math.abs(value) <= 1) return value.toFixed(4);
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(value);
}

export function DataTable({ rows, maxRows = 20 }: { rows: ApiRecord[]; maxRows?: number }) {
  if (!rows.length) return <p className="muted">No rows available.</p>;

  const columns = Object.keys(rows[0]).slice(0, 10);
  const visibleRows = rows.slice(0, maxRows);

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column.replaceAll("_", " ")}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visibleRows.map((row, index) => (
            <tr key={`${row.ticker ?? "row"}-${index}`}>
              {columns.map((column) => (
                <td key={column}>{formatCell(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
