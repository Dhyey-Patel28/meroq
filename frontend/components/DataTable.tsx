import type { ApiRecord } from "@/lib/api";

function isUrl(value: unknown) {
  if (typeof value !== "string") return false;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

function formatCell(value: ApiRecord[keyof ApiRecord]) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") {
    if (Math.abs(value) <= 1) return value.toFixed(4);
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(value);
}

function humanizeColumn(column: string) {
  return column.replaceAll("_", " ");
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
              <th key={column}>{humanizeColumn(column)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visibleRows.map((row, index) => (
            <tr key={`${row.ticker ?? row.title ?? "row"}-${index}`}>
              {tableColumns.map((column) => {
                const value = row[column];
                if (isUrl(value)) {
                  return (
                    <td key={column}>
                      <a className="table-link" href={String(value)} target="_blank" rel="noopener noreferrer">
                        Open source ↗
                      </a>
                    </td>
                  );
                }
                return <td key={column}>{formatCell(value)}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
