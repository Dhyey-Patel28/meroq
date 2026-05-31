import type { ApiRecord } from "@/lib/api";
import { formatNumber } from "@/lib/api";
import { StatusPill } from "@/components/StatusPill";

function sentimentTone(label: unknown): "neutral" | "positive" | "negative" | "warning" {
  const text = String(label ?? "").toLowerCase();
  if (text.includes("positive")) return "positive";
  if (text.includes("negative") || text.includes("caution")) return "negative";
  if (text.includes("irrelevant") || text.includes("uncertain")) return "neutral";
  if (text.includes("neutral")) return "warning";
  return "neutral";
}

function relevanceTone(label: unknown): "neutral" | "positive" | "negative" | "warning" {
  const text = String(label ?? "").toLowerCase();
  if (text.includes("high")) return "positive";
  if (text.includes("medium")) return "warning";
  if (text.includes("low")) return "neutral";
  return "neutral";
}

function safeUrl(value: unknown): string {
  const text = String(value ?? "").trim();
  if (!text) return "";
  try {
    const url = new URL(text);
    if (url.protocol === "http:" || url.protocol === "https:") return url.toString();
  } catch {
    return "";
  }
  return "";
}

function publishedText(value: unknown): string {
  if (!value) return "Recently published";
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function reasonTags(value: unknown): string[] {
  return String(value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 4);
}

export function NewsCard({ row }: { row: ApiRecord }) {
  const title = String(row.title ?? row.short_title ?? "Untitled headline");
  const publisher = String(row.publisher ?? row.source ?? "News source");
  const source = String(row.source ?? "news");
  const url = safeUrl(row.url);
  const label = String(row.target_sentiment_label ?? row.sentiment_label ?? "Unscored");
  const relevance = String(row.target_relevance_label ?? "Unknown relevance");
  const score = row.sentiment_score;
  const confidence = row.confidence;
  const explanation = String(row.sentiment_explanation ?? "").trim();
  const tags = reasonTags(row.reason_tags);

  return (
    <article className="news-card">
      <div className="news-card-topline">
        <span>{publisher}</span>
        <span>{publishedText(row.published_at)}</span>
      </div>

      <h3>{title}</h3>

      <div className="news-card-meta">
        <StatusPill label={label} tone={sentimentTone(label)} />
        <StatusPill label={relevance} tone={relevanceTone(relevance)} />
        <span>Score {formatNumber(score, 2)}</span>
        <span>Confidence {Number.isFinite(Number(confidence)) ? `${(Number(confidence) * 100).toFixed(0)}%` : "N/A"}</span>
        <span>{source}</span>
      </div>

      {explanation ? <p className="news-explanation">{explanation}</p> : null}

      {tags.length ? (
        <div className="reason-tags" aria-label="Sentiment reason tags">
          {tags.map((tag) => (
            <span key={tag}>{tag.replaceAll("-", " ")}</span>
          ))}
        </div>
      ) : null}

      {url ? (
        <a className="source-link" href={url} target="_blank" rel="noopener noreferrer">
          Open source article ↗
        </a>
      ) : (
        <span className="muted small">No source link returned by provider.</span>
      )}
    </article>
  );
}
