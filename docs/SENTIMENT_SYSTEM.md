# Sentiment System

Meroq provides a layered sentiment system.

## Engines

- Lightweight financial lexicon
- `ProsusAI/finbert`
- `yiyanghkust/finbert-tone`
- `mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis`
- Finance sentiment ensemble

## Fallback behavior

If optional NLP packages are not installed or a Hugging Face model cannot load, the app falls back to the lightweight financial lexicon.

## Local inference

Hugging Face models run locally after first download. No Hugging Face API key is required for the public models used here.

## Company-aware news matching

Meroq resolves each ticker into a company profile before broad news search. For example, an ambiguous ticker such as `PLAY` is treated as Dave & Buster's rather than the common word "play".

The news layer now uses:

- company name and alias generation;
- company-name-first NewsAPI queries;
- ticker-context matching such as `(PLAY)`, `NYSE:PLAY`, or `PLAY stock`;
- finance-context terms such as earnings, shares, revenue, analyst, and price target;
- relevance scores before sentiment scoring.

Broad NewsAPI rows that only match generic words are filtered out before they can affect sentiment. Cached news is filtered again at read time so older irrelevant cache rows do not pollute the current analysis.

## Signal fusion

Meroq can use recent-news sentiment as an overlay on top of the base model prediction. The overlay is conservative: sentiment is capped by a user-selected maximum adjustment and weighted by confidence, headline count, and ensemble agreement when available.

The final output shows:

- base model signal;
- base model up probability;
- sentiment adjustment;
- adjusted up probability;
- final sentiment-aware signal.

This design is intentionally transparent and should not be confused with a fully historical sentiment-trained model.


## Target-aware sentiment trust layer

Meroq 1.9.0 adds a deterministic correction layer after the selected sentiment engine. The goal is to answer a product-specific question: is this headline positive, cautionary, neutral, irrelevant, or uncertain for the selected ticker/company?

The layer adds these headline fields:

- `target_sentiment_label`
- `target_relevance_label`
- `target_relevance_score`
- `reason_tags`
- `sentiment_explanation`
- `base_sentiment_label` and `base_sentiment_score` for auditability

Known failure mode fixed: generic sentiment can mark “3 Reasons PLAY is Risky and 1 Stock to Buy Instead” as positive because it sees “stock to buy.” Target-aware scoring recognizes that PLAY is the risky target and the buy recommendation is for another stock.

Low-relevance and uncertain headlines are excluded from ticker-level sentiment aggregation when possible so broad or ambiguous headlines do not distort the overlay.


## Evaluation harness

Release 1.9.2 adds a local gold-labeled benchmark at `data/sentiment_gold/financial_headlines_gold.csv` and a CLI at `scripts/evaluate_sentiment.py`. Use it before changing target-aware rules or model selection. The benchmark emphasizes relevance, target sentiment, cautionary recall, and ambiguous ticker collisions.

```powershell
python scripts/evaluate_sentiment.py --engine lightweight --fail-under-accuracy 0.90 --fail-under-cautionary-recall 0.90
```
