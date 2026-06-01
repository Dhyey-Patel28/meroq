# Watchlist Screener Command Center

Release 1.9.5 turns the watchlist from a ranked table into a screener-style research queue.

## Goal

The watchlist page should answer:

```text
Which names deserve deeper inspection, which need risk review, and which rows need cleanup?
```

It is still a research tool, not a trading system.

## Row fields

Successful watchlist rows include:

- `watchlist_bucket` — the row's current queue
- `research_priority` — a local 0-100 triage priority
- `evidence_count` — recent scored headline count
- `scan_note` — plain-English explanation of the row's queue

Failed rows are labeled as `Data issue` and preserve the user-facing error message.

## Buckets

```text
Research queue  = stronger score/grade/probability setup
Momentum watch  = constructive but needs confirmation
Risk review     = high downside, cautionary sentiment, weak grade, or low score
Low priority    = usable but lower priority
Data issue      = could not analyze the symbol
```

## Summary fields

`POST /watchlist/scan` now returns summary fields for:

- `top_research_candidates`
- `momentum_watch`
- `risk_review`
- `sentiment_watch`
- `data_issues`
- `grade_distribution`
- `scan_alerts`

These fields are generated locally from existing Meroq score, grade, sentiment, and risk fields. No paid data dependency is added.

## UI behavior

The Next.js watchlist page keeps progressive one-ticker-at-a-time loading. As rows finish, it recomputes:

- research queue count
- risk-review count
- average Meroq Score
- best candidate card
- risk-review card
- sentiment-watch card
- ranked screener table

The user can filter the table by queue and export the visible rows as CSV.
