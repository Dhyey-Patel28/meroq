import type { ApiRecord } from "@/lib/api";

function formatCell(value: ApiRecord[keyof ApiRecord]) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") {
    if (Math.abs(value) <= 1) return value.toFixed(4);
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(value);
}

export function DataTable({
  rows,
  columns,
  maxRows = 20,
}: {
  rows: ApiRecord[];
  columns?: string[];
  maxRows?: number;
}) {
  if (!rows.length) return <p className="muted">No rows available yet.</p>;

  const tableColumns = columns?.length ? columns : Object.keys(rows[0]).slice(0, 10);
  const visibleRows = rows.slice(0, maxRows);

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {tableColumns.map((column) => (
              <th key={column}>{column.replaceAll("_", " ")}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visibleRows.map((row, index) => (
            <tr key={`${row.ticker ?? "row"}-${index}`}>
              {tableColumns.map((column) => (
                <td key={column}>{formatCell(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
