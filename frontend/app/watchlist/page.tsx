"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { StockDetailModal } from "@/components/StockDetailModal";
import { ErrorBox } from "@/components/StateBlocks";
import { MetricCard } from "@/components/MetricCard";
import { PageShell } from "@/components/PageShell";
import { StatusPill } from "@/components/StatusPill";
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
  "watchlist_bucket",
  "research_priority",
  "latest_close",
  "final_up_probability",
  "meroq_grade",
  "sentiment_label",
  "risk_label",
  "risk_loss_gt_5pct",
  "evidence_count",
  "scan_note",
];

type WatchlistFilter = "all" | "ready" | "research" | "momentum" | "risk" | "issues";

const CUSTOM_PRESET_KEY = "meroq.watchlist.presets.v1";

function rowStatus(row: ApiRecord) {
  return String(row.status ?? "").toLowerCase();
}

function bucket(row: ApiRecord) {
  return String(row.watchlist_bucket ?? "");
}

function isReady(row: ApiRecord) {
  return rowStatus(row) === "ok";
}

function isIssue(row: ApiRecord) {
  return rowStatus(row) === "failed" || bucket(row) === "Data issue";
}

function byPriority(rows: ApiRecord[]) {
  return [...rows].sort((a, b) => Number(b.research_priority ?? b.meroq_score ?? -Infinity) - Number(a.research_priority ?? a.meroq_score ?? -Infinity));
}

function buildSummary(rows: ApiRecord[]) {
  const okRows = rows.filter(isReady);
  const issueRows = rows.filter(isIssue);
  const researchRows = okRows.filter((row) => bucket(row) === "Research queue");
  const momentumRows = okRows.filter((row) => bucket(row) === "Momentum watch");
  const riskRows = okRows.filter((row) => bucket(row) === "Risk review");
  const lowPriorityRows = okRows.filter((row) => bucket(row) === "Low priority");
  const averageScore = okRows.length ? okRows.reduce((sum, row) => sum + Number(row.meroq_score ?? 0), 0) / okRows.length : null;
  const topCandidates = byPriority(researchRows.length ? researchRows : okRows).slice(0, 5);

  return {
    scanned: rows.length,
    ready: okRows.length,
    issues: issueRows.length,
    bullish: okRows.filter((row) => String(row.final_signal ?? "").toLowerCase() === "bullish").length,
    highRisk: riskRows.length,
    research: researchRows.length,
    momentum: momentumRows.length,
    risk: riskRows.length,
    lowPriority: lowPriorityRows.length,
    averageScore,
    topCandidates,
    topRisk: [...riskRows].sort((a, b) => Number(b.risk_loss_gt_5pct ?? -Infinity) - Number(a.risk_loss_gt_5pct ?? -Infinity)).slice(0, 5),
    sentimentWatch: okRows
      .filter((row) => String(row.sentiment_label ?? "").toLowerCase().match(/caution|negative|bearish/))
      .slice(0, 5),
  };
}

function sortRows(rows: ApiRecord[]) {
  return [...rows].sort((a, b) => {
    const aOk = isReady(a) ? 1 : 0;
    const bOk = isReady(b) ? 1 : 0;
    if (aOk !== bOk) return bOk - aOk;
    return Number(b.research_priority ?? b.meroq_score ?? -Infinity) - Number(a.research_priority ?? a.meroq_score ?? -Infinity);
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

function toneForSeverity(value: unknown): "neutral" | "positive" | "negative" | "warning" {
  const text = String(value ?? "").toLowerCase();
  if (text.includes("positive") || text.includes("research")) return "positive";
  if (text.includes("negative") || text.includes("risk") || text.includes("issue")) return "warning";
  return "neutral";
}

function CommandInsight({ title, detail, ticker, severity = "neutral" }: { title: string; detail: string; ticker?: string; severity?: string }) {
  const tone = toneForSeverity(severity);
  return (
    <section className={`insight-card tone-${tone}`}>
      <div className="card-heading-row">
        <div>
          <p className="status-label">Screener insight</p>
          <h3>{title}</h3>
        </div>
        {ticker ? <StatusPill label={ticker} tone={tone} /> : null}
      </div>
      <p className="muted">{detail}</p>
    </section>
  );
}

function ScreenerList({ title, rows, metric }: { title: string; rows: ApiRecord[]; metric: "priority" | "risk" | "score" }) {
  return (
    <section className="card contributor-card watchlist-queue-card">
      <div className="card-heading-row">
        <h3>{title}</h3>
        <span className="muted small">Top {rows.length || 0}</span>
      </div>
      {rows.length ? (
        <div className="contributor-list">
          {rows.map((row) => (
            <div className="contributor-row" key={`${title}-${String(row.ticker)}`}>
              <div>
                <strong>{String(row.ticker)}</strong>
                <p className="muted small">{String(row.scan_note ?? row.watchlist_bucket ?? "Watchlist row")}</p>
              </div>
              <div className="contributor-metric">
                {metric === "risk"
                  ? `${((Number(row.risk_loss_gt_5pct ?? 0) || 0) * 100).toFixed(1)}%`
                  : metric === "priority"
                    ? String(row.research_priority ?? "N/A")
                    : formatNumber(row.meroq_score)}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">Run a scan to populate this queue.</p>
      )}
    </section>
  );
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
  const [statusFilter, setStatusFilter] = useState<WatchlistFilter>("all");
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
            : row.scan_note ?? (row.headline_count ? `${String(row.headline_count)} headlines reviewed` : "Ready"),
      })),
    [rows],
  );

  const filteredRows = useMemo(() => {
    if (statusFilter === "ready") return sortedRows.filter(isReady);
    if (statusFilter === "issues") return sortedRows.filter(isIssue);
    if (statusFilter === "research") return sortedRows.filter((row) => bucket(row) === "Research queue");
    if (statusFilter === "momentum") return sortedRows.filter((row) => bucket(row) === "Momentum watch");
    if (statusFilter === "risk") return sortedRows.filter((row) => bucket(row) === "Risk review");
    return sortedRows;
  }, [sortedRows, statusFilter]);

  const readyTickers = sortedRows.filter(isReady).map((row) => String(row.ticker));
  const issueTickers = sortedRows.filter(isIssue).map((row) => String(row.ticker));

  const top = summary.topCandidates
    .slice(0, 3)
    .map((row) => String(row.ticker))
    .join(", ");
  const topCandidate = summary.topCandidates[0];
  const topRisk = summary.topRisk[0];
  const topSentiment = summary.sentimentWatch[0];

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
        <p className="eyebrow">Watchlist screener</p>
        <h1>Turn a messy ticker list into a focused research queue.</h1>
        <p>Save reusable ticker sets, clean pasted lists, and separate candidates, momentum watches, risk reviews, and data issues as rows finish loading.</p>
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
          <MetricCard label="Research queue" value={String(summary.research)} helper="Highest-priority candidates" tone="positive" />
          <MetricCard label="Risk review" value={String(summary.risk)} helper="Needs caution before deep dive" tone={summary.risk ? "warning" : "neutral"} />
          <MetricCard label="Avg score" value={summary.averageScore === null ? "N/A" : formatNumber(summary.averageScore)} helper={`Ready: ${summary.ready} · Issues: ${summary.issues}`} />
        </section>
      ) : null}

      {rows.length ? (
        <section className="card callout-card" style={{ marginTop: 18 }}>
          <p className="status-label">Quick read</p>
          <h2>Highest-priority ready names: {top || "Still loading"}</h2>
          <p className="muted">The screener now separates research candidates from momentum watches, risk reviews, low-priority rows, and data cleanup items.</p>
        </section>
      ) : null}

      {rows.length ? (
        <section className="watchlist-command-grid" style={{ marginTop: 18 }}>
          <CommandInsight
            title="Best research candidate"
            ticker={topCandidate ? String(topCandidate.ticker) : undefined}
            severity="positive"
            detail={topCandidate ? String(topCandidate.scan_note ?? "Highest priority row in this scan.") : "No research candidate has emerged yet."}
          />
          <CommandInsight
            title="Risk review queue"
            ticker={topRisk ? String(topRisk.ticker) : undefined}
            severity={topRisk ? "warning" : "neutral"}
            detail={topRisk ? String(topRisk.scan_note ?? "Review risk before deeper research.") : "No ready rows currently require a risk-review queue."}
          />
          <CommandInsight
            title="Sentiment watch"
            ticker={topSentiment ? String(topSentiment.ticker) : undefined}
            severity={topSentiment ? "warning" : "neutral"}
            detail={topSentiment ? String(topSentiment.scan_note ?? "Recent headlines need source inspection.") : "No cautionary sentiment rows are visible yet."}
          />
          <CommandInsight
            title="Data cleanup"
            severity={summary.issues ? "warning" : "neutral"}
            detail={summary.issues ? `${summary.issues} ticker${summary.issues === 1 ? "" : "s"} could not be analyzed.` : "No failed rows in this scan so far."}
          />
        </section>
      ) : null}

      {rows.length ? (
        <section className="watchlist-queue-grid" style={{ marginTop: 18 }}>
          <ScreenerList title="Research queue" rows={summary.topCandidates} metric="priority" />
          <ScreenerList title="Risk review" rows={summary.topRisk} metric="risk" />
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
              ["research", `Research (${summary.research})`],
              ["momentum", `Momentum (${summary.momentum})`],
              ["risk", `Risk review (${summary.risk})`],
              ["issues", `Issues (${summary.issues})`],
            ].map(([value, label]) => (
              <button
                className={`filter-chip ${statusFilter === value ? "active" : ""}`}
                type="button"
                key={value}
                onClick={() => setStatusFilter(value as WatchlistFilter)}
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
            <h2>Ranked screener</h2>
            <p className="muted small">Searchable, scrollable, row-clickable, and bucketed by research priority.</p>
          </div>
          {sortedRows.length ? <span className="muted small">Top priority: {String(sortedRows[0]?.research_priority ?? "N/A")}</span> : null}
        </div>
        <DataTable
          rows={filteredRows}
          columns={columns}
          searchPlaceholder="Search tickers, buckets, scores, signals, or notes…"
          onRowClick={(row) => setSelectedRow(row)}
          rowHint="Row details"
          exportFilename="meroq-watchlist-screener.csv"
          legend={
            <div className="legend-row">
              <span className="legend-pill positive">▲ Research queue</span>
              <span className="legend-pill warning">● Momentum / review</span>
              <span className="legend-pill negative">▼ Risk or data issue</span>
              <span className="legend-pill neutral">• Lower priority</span>
            </div>
          }
        />
      </section>

      <StockDetailModal ticker={selectedRow ? String(selectedRow.ticker ?? "") : null} period={period} baseRow={selectedRow} onClose={() => setSelectedRow(null)} />
    </PageShell>
  );
}
