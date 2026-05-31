export type TickerInputSummary = {
  rawCount: number;
  uniqueCount: number;
  duplicateCount: number;
  scanCount: number;
  skippedByLimit: number;
  uniqueSymbols: string[];
  duplicateSymbols: string[];
};

export type WatchlistPreset = {
  name: string;
  tickers: string[];
  createdAt?: string;
};

export const DEFAULT_WATCHLIST_PRESETS: WatchlistPreset[] = [
  {
    name: "Core market",
    tickers: ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "SPY", "QQQ"],
  },
  {
    name: "AI infrastructure",
    tickers: ["NVDA", "AVGO", "AMD", "TSM", "ASML", "AMAT", "LRCX", "ORCL", "SMCI"],
  },
  {
    name: "Fintech + crypto beta",
    tickers: ["MSTR", "COIN", "HOOD", "SOFI", "PYPL", "SQ", "V", "MA", "MARA"],
  },
  {
    name: "Consumer + autos",
    tickers: ["WMT", "COST", "TGT", "HD", "LOW", "SBUX", "MCD", "HOG", "F", "GM", "TSLA"],
  },
];

export function normalizeTickerInput(value: string): string[] {
  const seen = new Set<string>();
  const symbols: string[] = [];

  value
    .split(/[\s,;]+/)
    .map((item) => item.trim().toUpperCase())
    .filter(Boolean)
    .forEach((symbol) => {
      // Keep common suffixes such as BRK.B or RY.TO, but strip obvious text noise.
      const cleaned = symbol.replace(/[^A-Z0-9.\-]/g, "");
      if (!cleaned || seen.has(cleaned)) return;
      seen.add(cleaned);
      symbols.push(cleaned);
    });

  return symbols;
}

export function summarizeTickerInput(value: string, maxTickers: number): TickerInputSummary {
  const raw = value
    .split(/[\s,;]+/)
    .map((item) => item.trim().toUpperCase())
    .filter(Boolean);
  const counts = new Map<string, number>();
  raw.forEach((symbol) => counts.set(symbol, (counts.get(symbol) ?? 0) + 1));
  const uniqueSymbols = normalizeTickerInput(value);
  const duplicateSymbols = [...counts.entries()].filter(([, count]) => count > 1).map(([symbol]) => symbol);
  const safeMax = Math.max(1, maxTickers);

  return {
    rawCount: raw.length,
    uniqueCount: uniqueSymbols.length,
    duplicateCount: Math.max(0, raw.length - uniqueSymbols.length),
    scanCount: Math.min(uniqueSymbols.length, safeMax),
    skippedByLimit: Math.max(0, uniqueSymbols.length - safeMax),
    uniqueSymbols,
    duplicateSymbols,
  };
}

export function formatTickerList(tickers: string[]) {
  return normalizeTickerInput(tickers.join(",")).join(",");
}
