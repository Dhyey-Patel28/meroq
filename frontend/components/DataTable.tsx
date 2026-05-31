"use client";

import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import { InfoTip } from "@/components/InfoTip";
import { StatusPill } from "@/components/StatusPill";
import { type ApiRecord, formatNumber, formatPct } from "@/lib/api";

function isUrl(value: unknown) {
  if (typeof value !== "string") return false;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

function humanizeColumn(column: string) {
  return column.replaceAll("_", " ");
}

function toneFromText(value: string): "neutral" | "positive" | "negative" | "warning" {
  const text = value.toLowerCase();
  if (text.includes("bullish") || text.includes("positive") || text.includes("constructive") || text.includes("low")) {
    return "positive";
  }
  if (text.includes("bearish") || text.includes("negative") || text.includes("high") || text.includes("elevated") || text.includes("failed")) {
    return "negative";
  }
  if (text.includes("neutral") || text.includes("balanced") || text.includes("cautious") || text.includes("skipped")) {
    return "warning";
  }
  return "neutral";
}

function symbolForText(value: string) {
  const text = value.toLowerCase();
  if (text.includes("bullish") || text.includes("positive") || text.includes("constructive") || text === "ok") return "▲";
  if (text.includes("bearish") || text.includes("negative") || text.includes("high") || text === "failed") return "▼";
  if (text.includes("neutral") || text.includes("balanced") || text.includes("skipped")) return "●";
  return "•";
}

function formatCell(value: ApiRecord[keyof ApiRecord], column: string) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") {
    if (column.includes("probability") || column.includes("weight") || column.includes("return") || column.includes("loss_gt") || column.includes("score_pct")) {
      if (Math.abs(value) <= 1.5) return formatPct(value, 1);
    }
    if (Math.abs(value) <= 1) return value.toFixed(4);
    return formatNumber(value, 2);
  }
  return String(value);
}

function renderDecoratedCell(column: string, value: ApiRecord[keyof ApiRecord]) {
  if (column === "status") {
    const text = String(value ?? "Unknown");
    const label = text === "ok" ? "Ready" : text === "failed" ? "Issue" : text;
    return <StatusPill label={`${symbolForText(text)} ${label}`} tone={toneFromText(text)} />;
  }

  if (["final_signal", "sentiment_label", "risk_label"].includes(column) && value) {
    const text = String(value);
    return <StatusPill label={`${symbolForText(text)} ${text}`} tone={toneFromText(text)} />;
  }

  if (column === "error" && value) {
    const text = String(value);
    return (
      <span className="table-note" title={text}>
        {text}
      </span>
    );
  }

  if (isUrl(value)) {
    return (
      <a className="table-link" href={String(value)} target="_blank" rel="noopener noreferrer">
        Open source ↗
      </a>
    );
  }

  return formatCell(value, column);
}

function compareValues(a: ApiRecord, b: ApiRecord, column: string) {
  const left = a[column];
  const right = b[column];
  const leftNumber = Number(left);
  const rightNumber = Number(right);

  if (Number.isFinite(leftNumber) && Number.isFinite(rightNumber)) {
    return leftNumber - rightNumber;
  }

  return String(left ?? "").localeCompare(String(right ?? ""), undefined, {
    numeric: true,
    sensitivity: "base",
  });
}

function csvEscape(value: ApiRecord[keyof ApiRecord]) {
  const text = value === null || value === undefined ? "" : String(value);
  return `"${text.replaceAll('"', '""')}"`;
}

function downloadCsv(filename: string, rows: ApiRecord[], columns: string[]) {
  const header = columns.map(csvEscape).join(",");
  const body = rows.map((row) => columns.map((column) => csvEscape(row[column])).join(",")).join("\n");
  const csv = [header, body].filter(Boolean).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function DataTable({
  rows,
  columns,
  maxRows,
  searchable = true,
  searchPlaceholder = "Search this table…",
  onRowClick,
  rowHint,
  legend,
  exportFilename,
}: {
  rows: ApiRecord[];
  columns?: string[];
  maxRows?: number;
  searchable?: boolean;
  searchPlaceholder?: string;
  onRowClick?: (row: ApiRecord) => void;
  rowHint?: string;
  legend?: ReactNode;
  exportFilename?: string;
}) {
  const [query, setQuery] = useState("");
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const tableColumns = columns?.length ? columns : Object.keys(rows[0] ?? {}).slice(0, 10);

  const visibleRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    const source = maxRows ? rows.slice(0, maxRows) : rows;
    const searched = q
      ? source.filter((row) => tableColumns.some((column) => String(row[column] ?? "").toLowerCase().includes(q)))
      : source;

    if (!sortColumn) return searched;

    return [...searched].sort((a, b) => {
      const result = compareValues(a, b, sortColumn);
      return sortDirection === "asc" ? result : -result;
    });
  }, [maxRows, query, rows, sortColumn, sortDirection, tableColumns]);

  function toggleSort(column: string) {
    if (sortColumn === column) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortColumn(column);
    setSortDirection("desc");
  }

  if (!rows.length) return <p className="muted">No rows available yet.</p>;

  return (
    <div className="table-panel">
      {(searchable || legend || exportFilename) && (
        <div className="table-toolbar">
          {searchable ? (
            <label className="table-search">
              <span className="sr-only">Search table</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={searchPlaceholder}
                aria-label="Search rows"
              />
            </label>
          ) : (
            <span />
          )}
          <div className="table-toolbar-actions">
            <span className="muted small">Showing {visibleRows.length} of {rows.length}</span>
            {rowHint ? (
              <span className="muted small">
                {rowHint}
                <InfoTip label="Row interaction">Click a row to open a richer view for that ticker.</InfoTip>
              </span>
            ) : null}
            {exportFilename ? (
              <button className="secondary-button compact-button" type="button" onClick={() => downloadCsv(exportFilename, visibleRows, tableColumns)}>
                Export CSV
              </button>
            ) : null}
          </div>
        </div>
      )}

      {legend ? <div className="table-legend">{legend}</div> : null}

      <div className="table-wrap scroll-y">
        <table>
          <thead>
            <tr>
              {tableColumns.map((column) => {
                const active = sortColumn === column;
                return (
                  <th key={column}>
                    <button className="sort-button" type="button" onClick={() => toggleSort(column)}>
                      {humanizeColumn(column)} {active ? (sortDirection === "asc" ? "↑" : "↓") : ""}
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, index) => (
              <tr
                key={`${row.ticker ?? row.title ?? "row"}-${index}`}
                className={onRowClick ? "clickable-row" : undefined}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                tabIndex={onRowClick ? 0 : undefined}
                onKeyDown={
                  onRowClick
                    ? (event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          onRowClick(row);
                        }
                      }
                    : undefined
                }
              >
                {tableColumns.map((column) => (
                  <td key={column}>{renderDecoratedCell(column, row[column])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {query && !visibleRows.length ? <p className="muted small">No rows matched your search.</p> : null}
    </div>
  );
}
