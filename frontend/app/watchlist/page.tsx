"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { StockDetailModal } from "@/components/StockDetailModal";
import { ErrorBox } from "@/components/StateBlocks";
import { MetricCard } from "@/components/MetricCard";
import { PageShell } from "@/components/PageShell";
import { formatNumber, scanWatchlistOne, type ApiRecord, type WatchlistSinglePayload } from "@/lib/api";
import {
  DEFAULT_WATCHLIST_PRESETS,
  formatTickerList,
  summarizeTickerInput,
  type WatchlistPreset,
} from "@/lib/tickerTools";

const columns = [
  "status",
  "ticker",
  "latest_close",
  "final_signal",
  "final_up_probability",
  "meroq_grade",
  "sentiment_label",
  "risk_label",
  "meroq_score",
  "note",
];

const CUSTOM_PRESET_KEY = "meroq.watchlist.presets.v1";

function buildSummary(rows: ApiRecord[]) {
  const okRows = rows.filter((row) => String(row.status ?? "").toLowerCase() === "ok");
  return {
    scanned: rows.length,
    ready: okRows.length,
    issues: rows.length - okRows.length,
    bullish: okRows.filter((row) => String(row.final_signal ?? "").toLowerCase() === "bullish").length,
    highRisk: okRows.filter((row) => String(row.risk_label ?? "").toLowerCase().includes("high")).length,
  };
}

function sortRows(rows: ApiRecord[]) {
  return [...rows].sort((a, b) => {
    const aOk = String(a.status ?? "") === "ok" ? 1 : 0;
    const bOk = String(b.status ?? "") === "ok" ? 1 : 0;
    if (aOk !== bOk) return bOk - aOk;
    return Number(b.meroq_score ?? -Infinity) - Number(a.meroq_score ?? -Infinity);
  });
}

function loadCustomPresets(): WatchlistPreset[] {
  try {
    const stored = window.localStorage.getItem(CUSTOM_PRESET_KEY);
    if (!stored) return [];
    const parsed = JSON.parse(stored) as WatchlistPreset[];
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((preset) => preset?.name && Array.isArray(preset.tickers));
  } catch {
    return [];
  }
}

function persistCustomPresets(presets: WatchlistPreset[]) {
  window.localStorage.setItem(CUSTOM_PRESET_KEY, JSON.stringify(presets));
}

export default function WatchlistPage() {
  const [tickers, setTickers] = useState("AAPL,MSFT,NVDA,GOOGL,SPY");
  const [period, setPeriod] = useState("5y");
  const [maxTickers, setMaxTickers] = useState(40);
  const [rows, setRows] = useState<ApiRecord[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentTicker, setCurrentTicker] = useState("");
  const [selectedRow, setSelectedRow] = useState<ApiRecord | null>(null);
  const [statusFilter, setStatusFilter] = useState<"all" | "ready" | "issues" | "high-risk">("all");
  const [copyMessage, setCopyMessage] = useState("");
  const [presetName, setPresetName] = useState("");
  const [customPresets, setCustomPresets] = useState<WatchlistPreset[]>([]);
  const stopRef = useRef(false);

  useEffect(() => {
    setCustomPresets(loadCustomPresets());
  }, []);

  const inputSummary = useMemo(() => summarizeTickerInput(tickers, maxTickers), [maxTickers, tickers]);
  const summary = useMemo(() => buildSummary(rows), [rows]);
  const sortedRows = useMemo<ApiRecord[]>(
    () =>
      sortRows(rows).map((row) => ({
        ...row,
        note:
          String(row.status ?? "") === "failed"
            ? row.error ?? "Data issue"
            : row.headline_count
              ? `${String(row.headline_count)} headlines reviewed`
              : "Ready",
      })),
    [rows],
  );

  const filteredRows = useMemo(() => {
    if (statusFilter === "ready") return sortedRows.filter((row) => String(row.status ?? "") === "ok");
    if (statusFilter === "issues") return sortedRows.filter((row) => String(row.status ?? "") === "failed");
    if (statusFilter === "high-risk") {
      return sortedRows.filter((row) => String(row.risk_label ?? "").toLowerCase().includes("high"));
    }
    return sortedRows;
  }, [sortedRows, statusFilter]);

  const readyTickers = sortedRows.filter((row) => String(row.status ?? "") === "ok").map((row) => String(row.ticker));
  const issueTickers = sortedRows.filter((row) => String(row.status ?? "") === "failed").map((row) => String(row.ticker));

  const top = sortedRows
    .filter((row) => String(row.status ?? "") === "ok")
    .slice(0, 3)
    .map((row) => String(row.ticker))
    .join(", ");

  function loadPreset(preset: WatchlistPreset) {
    setTickers(formatTickerList(preset.tickers));
    setRows([]);
    setStatusFilter("all");
    setCopyMessage(`Loaded preset: ${preset.name}.`);
  }

  function saveCurrentPreset() {
    const name = presetName.trim();
    if (!name) {
      setCopyMessage("Add a preset name before saving.");
      return;
    }
    if (!inputSummary.uniqueSymbols.length) {
      setCopyMessage("Add at least one ticker before saving a preset.");
      return;
    }
    const nextPreset: WatchlistPreset = {
      name,
      tickers: inputSummary.uniqueSymbols,
      createdAt: new Date().toISOString(),
    };
    const next = [nextPreset, ...customPresets.filter((preset) => preset.name.toLowerCase() !== name.toLowerCase())].slice(0, 12);
    setCustomPresets(next);
    persistCustomPresets(next);
    setPresetName("");
    setCopyMessage(`Saved preset: ${name}.`);
  }

  function deletePreset(name: string) {
    const next = customPresets.filter((preset) => preset.name !== name);
    setCustomPresets(next);
    persistCustomPresets(next);
    setCopyMessage(`Deleted preset: ${name}.`);
  }

  async function copyTickers(label: string, symbols: string[]) {
    const value = symbols.join(",");
    if (!value) {
      setCopyMessage(`No ${label} tickers to copy.`);
      return;
    }
    await navigator.clipboard.writeText(value);
    setCopyMessage(`Copied ${symbols.length} ${label} ticker${symbols.length === 1 ? "" : "s"}.`);
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setRows([]);
    setCurrentTicker("");
    setCopyMessage("");
    setStatusFilter("all");
    stopRef.current = false;

    const symbols = inputSummary.uniqueSymbols.slice(0, Math.max(1, maxTickers));
    const basePayload: Omit<WatchlistSinglePayload, "ticker"> = {
      period,
      interval: "1d",
      include_sentiment: true,
      include_risk: true,
      news_source: "all_configured",
      sentiment_engine: "lightweight",
      max_news_items: 10,
      risk_paths: 300,
      risk_horizon: 30,
      days_back: 7,
    };

    try {
      for (const symbol of symbols) {
        if (stopRef.current) break;
        setCurrentTicker(symbol);
        const response = await scanWatchlistOne({ ...basePayload, ticker: symbol });
        setRows((current) => [...current, response.row]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Watchlist scan failed.");
    } finally {
      stopRef.current = false;
      setLoading(false);
      setCurrentTicker("");
    }
  }

  return (
    <PageShell>
      <section className="hero compact-hero">
        <p className="eyebrow">Watchlist scan</p>
        <h1>Rank a working watchlist as rows finish loading.</h1>
        <p>Save reusable ticker sets, clean messy pasted lists, and scan only the symbols that are ready.</p>
      </section>

      <form className="card form" onSubmit={onSubmit}>
        <label>
          Watchlist tickers
          <textarea rows={4} value={tickers} onChange={(event) => setTickers(event.target.value)} />
        </label>

        <section className="input-hygiene-panel">
          <div>
            <p className="status-label">Input hygiene</p>
            <h3>{inputSummary.uniqueCount} unique ticker{inputSummary.uniqueCount === 1 ? "" : "s"}</h3>
            <p className="muted small">
              {inputSummary.rawCount} entered · {inputSummary.duplicateCount} duplicate{inputSummary.duplicateCount === 1 ? "" : "s"} removed · {inputSummary.scanCount} queued
              {inputSummary.skippedByLimit ? ` · ${inputSummary.skippedByLimit} held by max limit` : ""}
            </p>
          </div>
          <div className="button-row">
            <button
              className="secondary-button"
              type="button"
              onClick={() => {
                setTickers(formatTickerList(inputSummary.uniqueSymbols));
                setCopyMessage("Cleaned and deduplicated the input list.");
              }}
            >
              Clean list
            </button>
            <button className="secondary-button" type="button" onClick={() => copyTickers("clean", inputSummary.uniqueSymbols)}>
              Copy clean list
            </button>
          </div>
        </section>

        <section className="preset-panel">
          <div className="card-heading-row">
            <div>
              <p className="status-label">Presets</p>
              <h3>Reusable watchlists</h3>
            </div>
          </div>
          <div className="preset-grid">
            {DEFAULT_WATCHLIST_PRESETS.map((preset) => (
              <button className="preset-card" type="button" key={preset.name} onClick={() => loadPreset(preset)}>
                <strong>{preset.name}</strong>
                <span>{preset.tickers.slice(0, 5).join(", ")}{preset.tickers.length > 5 ? "…" : ""}</span>
              </button>
            ))}
          </div>
          <div className="preset-save-row">
            <label>
              Save current list as
              <input value={presetName} onChange={(event) => setPresetName(event.target.value)} placeholder="Example: My AI watchlist" />
            </label>
            <button className="secondary-button" type="button" onClick={saveCurrentPreset}>
              Save preset
            </button>
          </div>
          {customPresets.length ? (
            <div className="saved-preset-list">
              {customPresets.map((preset) => (
                <div className="saved-preset-row" key={preset.name}>
                  <button className="text-button" type="button" onClick={() => loadPreset(preset)}>
                    {preset.name} · {preset.tickers.length} tickers
                  </button>
                  <button className="danger-link" type="button" onClick={() => deletePreset(preset.name)}>
                    Delete
                  </button>
                </div>
              ))}
            </div>
          ) : null}
        </section>

        <div className="grid cols-2">
          <label>
            History period
            <select value={period} onChange={(event) => setPeriod(event.target.value)}>
              <option value="1y">1y</option>
              <option value="5y">5y</option>
              <option value="10y">10y</option>
              <option value="max">max</option>
            </select>
          </label>
          <label>
            Max tickers this scan
            <input
              type="number"
              min={1}
              max={200}
              value={maxTickers}
              onChange={(event) => setMaxTickers(Number(event.target.value) || 1)}
            />
          </label>
        </div>
        <div className="button-row">
          <button disabled={loading || !inputSummary.uniqueSymbols.length}>{loading ? "Scanning…" : "Run watchlist scan"}</button>
          <button
            type="button"
            className="secondary-button"
            disabled={!loading}
            onClick={() => {
              stopRef.current = true;
            }}
          >
            Stop scan
          </button>
        </div>
        <p className="muted small">
          Large local universes can take a while. Start with 25–40 names, then expand. Symbols that cannot be downloaded are skipped and labeled.
        </p>
      </form>

      {copyMessage ? <p className="muted small form-status">{copyMessage}</p> : null}

      {loading ? (
        <section className="card subtle-card" style={{ marginTop: 18 }}>
          <div className="loader-row">
            <span className="spinner" />
            <div>
              <h3>Scanning {currentTicker || "watchlist"}…</h3>
              <p className="muted">Rows are added as soon as each ticker finishes.</p>
            </div>
          </div>
          <div className="progress-inline">
            <div className="progress-track" aria-hidden="true">
              <div
                className="progress-fill"
                style={{ width: `${Math.min(100, (summary.scanned / Math.max(1, inputSummary.scanCount)) * 100)}%` }}
              />
            </div>
            <span className="muted small">
              {summary.scanned}/{inputSummary.scanCount} completed
            </span>
          </div>
        </section>
      ) : null}

      {error ? <ErrorBox message={error} /> : null}

      {rows.length ? (
        <section className="grid cols-4" style={{ marginTop: 18 }}>
          <MetricCard label="Completed" value={String(summary.scanned)} helper="Rows returned so far" />
          <MetricCard label="Ready" value={String(summary.ready)} helper="Usable analyses" tone="positive" />
          <MetricCard label="Top grade" value={String(sortedRows.find((row) => row.meroq_grade)?.meroq_grade ?? "N/A")} helper="Best currently ranked row" />
          <MetricCard label="Issues" value={String(summary.issues)} helper="Skipped or unavailable" tone={summary.issues ? "warning" : "neutral"} />
          <MetricCard label="Bullish" value={String(summary.bullish)} helper={`High risk names: ${summary.highRisk}`} />
        </section>
      ) : null}

      {rows.length ? (
        <section className="card callout-card" style={{ marginTop: 18 }}>
          <p className="status-label">Quick read</p>
          <h2>Highest-ranked ready names: {top || "Still loading"}</h2>
          <p className="muted">Use filters for cleanup, export visible rows as CSV, or copy ready/issue tickers for the next scan.</p>
        </section>
      ) : null}

      {rows.length ? (
        <section className="card" style={{ marginTop: 18 }}>
          <div className="card-heading-row">
            <div>
              <p className="status-label">Result controls</p>
              <h2>Clean up this scan</h2>
            </div>
          </div>
          <div className="filter-row" role="group" aria-label="Watchlist result filters">
            {[
              ["all", `All (${sortedRows.length})`],
              ["ready", `Ready (${summary.ready})`],
              ["issues", `Issues (${summary.issues})`],
              ["high-risk", `High risk (${summary.highRisk})`],
            ].map(([value, label]) => (
              <button
                className={`filter-chip ${statusFilter === value ? "active" : ""}`}
                type="button"
                key={value}
                onClick={() => setStatusFilter(value as typeof statusFilter)}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="button-row" style={{ marginTop: 14 }}>
            <button className="secondary-button" type="button" onClick={() => copyTickers("ready", readyTickers)}>
              Copy ready tickers
            </button>
            <button className="secondary-button" type="button" onClick={() => copyTickers("issue", issueTickers)}>
              Copy issue tickers
            </button>
            <button
              className="secondary-button"
              type="button"
              disabled={!issueTickers.length}
              onClick={() => {
                setTickers(issueTickers.join(","));
                setRows([]);
                setStatusFilter("all");
                setCopyMessage("Issue tickers loaded into the input for review.");
              }}
            >
              Review issue tickers
            </button>
          </div>
        </section>
      ) : null}

      <section className="card" style={{ marginTop: 18 }}>
        <div className="card-heading-row">
          <div>
            <h2>Ranked scan</h2>
            <p className="muted small">Searchable, scrollable, and row-clickable.</p>
          </div>
          {sortedRows.length ? <span className="muted small">Top score: {formatNumber(sortedRows[0]?.meroq_score)}</span> : null}
        </div>
        <DataTable
          rows={filteredRows}
          columns={columns}
          searchPlaceholder="Search tickers, scores, signals, or issue notes…"
          onRowClick={(row) => setSelectedRow(row)}
          rowHint="Row details"
          exportFilename="meroq-watchlist-scan.csv"
          legend={
            <div className="legend-row">
              <span className="legend-pill positive">▲ Bullish / positive</span>
              <span className="legend-pill warning">● Neutral / balanced</span>
              <span className="legend-pill negative">▼ Bearish / higher concern</span>
              <span className="legend-pill neutral">⚠ Data issue</span>
            </div>
          }
        />
      </section>

      <StockDetailModal ticker={selectedRow ? String(selectedRow.ticker ?? "") : null} period={period} baseRow={selectedRow} onClose={() => setSelectedRow(null)} />
    </PageShell>
  );
}
