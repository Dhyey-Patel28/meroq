# Sentiment Evaluation Harness

Meroq's sentiment layer is target-aware: the question is not whether a headline sounds positive in isolation, but whether it is positive, cautionary, neutral, irrelevant, or uncertain for the selected ticker.

## Gold dataset

The local benchmark lives at:

```text
data/sentiment_gold/financial_headlines_gold.csv
```

Each row includes:

- `ticker`
- `company_name`
- `company_aliases`
- `relevance_score`
- `title`
- `summary`
- `expected_target_sentiment`
- `expected_sentiment_label`
- `expected_relevance_label`
- `reason`

The initial benchmark intentionally includes failure-prone patterns:

- risky / buy-instead headlines
- ambiguous tickers such as PLAY and SQ
- direct positive events such as beats, raises, rallies, gains
- direct cautionary events such as lawsuits, downgrades, misses, warnings, drops
- irrelevant non-financial headlines that happen to contain a company alias

## Run evaluation

```powershell
python scripts/evaluate_sentiment.py --engine lightweight
```

Optional regression gates:

```powershell
python scripts/evaluate_sentiment.py `
  --engine lightweight `
  --fail-under-accuracy 0.90 `
  --fail-under-cautionary-recall 0.90
```

Optional detailed output:

```powershell
python scripts/evaluate_sentiment.py `
  --engine lightweight `
  --output data/sentiment_gold/latest_eval_details.csv
```

Do not commit generated evaluation outputs unless they are intentionally curated as benchmark data.

## Metrics

The harness reports:

- target accuracy
- target macro-F1
- relevance accuracy
- relevance macro-F1
- cautionary recall
- positive recall
- irrelevant recall
- average latency per headline
- mismatch counts

## Why this matters

A generic sentiment model can mislabel a headline like:

```text
3 Reasons PLAY is Risky and 1 Stock to Buy Instead
```

as positive because it sees "stock to buy." Meroq's target-aware benchmark requires this to be cautionary for PLAY, because the selected company is the one being described as risky.

## Next benchmark expansions

Add more rows for:

- earnings calls and guidance nuance
- analyst upgrades/downgrades with mixed price targets
- multi-company headlines where one company benefits and another is harmed
- ETF/index headlines
- sector-wide headlines
- highly ambiguous tickers such as A, ON, NOW, GO, RUN, AI, PLAY, and SQ
