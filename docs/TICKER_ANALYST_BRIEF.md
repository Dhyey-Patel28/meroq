# Ticker analyst brief

Release 1.9.6 adds a local analyst-style brief to single-ticker analysis.

The goal is to make the ticker page feel like a research one-pager instead of a pile of raw metrics. The brief starts with the most useful interpretation, then points the user toward the evidence that should be inspected next.

## Response shape

Ticker analysis responses include a top-level `brief` object:

```text
brief
├── ticker
├── stance_label
├── stance_tone
├── conviction_label
├── conviction_tone
├── primary_driver
├── evidence_quality
├── evidence_tone
├── risk_read
├── risk_tone
├── sentiment_read
├── sentiment_tone
├── brief_sentence
├── key_points[]
├── watch_items[]
└── research_checks[]
```

## Stance labels

The stance label is a research-triage read, not advice:

```text
Constructive research setup
Constructive but needs confirmation
Balanced / watch
Cautionary review
Insufficient evidence
```

It uses the final up-probability, Meroq Grade, downside-risk probability, and recent sentiment score.

## Conviction labels

Conviction is based on how far the probability is from 50/50, whether the grade is supportive, whether news evidence exists, and whether the risk lens is available:

```text
Higher conviction
Moderate conviction
Low conviction
Unknown conviction
```

Close-to-balanced probabilities intentionally remain low conviction even when the direction is slightly constructive.

## Primary driver

The primary driver explains what is carrying or constraining the read:

```text
Risk lens is the main constraint
Recent news meaningfully changed the read
Model signal is the main driver
Grade quality is carrying the setup
No single dominant driver
```

## Evidence quality

Evidence quality is a practical trust label:

```text
Broad evidence
Partial evidence
Thin evidence
```

It considers headline count, risk availability, model diagnostics, and training rows. The label is intentionally conservative because a ticker can have a strong-looking score with thin evidence.

## Watch items and research checks

The brief includes two action-oriented lists:

```text
watch_items
```

These are flags to review, such as elevated downside risk, missing headlines, cautionary sentiment, low conviction, or weak grades.

```text
research_checks
```

These are next research steps, such as opening source-backed headlines, comparing component grades to peers, and checking whether the risk horizon matches the user's timeframe.

## Design constraints

The brief is:

```text
local-first
free to run
source-aware
explainable
research-oriented
```

It is not:

```text
a buy/sell engine
portfolio allocation advice
a replacement for filings or professional research
paid-data dependent
```
