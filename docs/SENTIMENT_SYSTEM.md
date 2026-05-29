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

## Current limitation

Sentiment is currently displayed as context. The next modeling step is to save dated sentiment features and compare models with vs. without sentiment features.


## Signal fusion

Meroq can use recent-news sentiment as an overlay on top of the base model prediction. The overlay is conservative: sentiment is capped by a user-selected maximum adjustment and weighted by confidence, headline count, and ensemble agreement when available.

The final output shows:

- base model signal;
- base model up probability;
- sentiment adjustment;
- adjusted up probability;
- final sentiment-aware signal.

This design is intentionally transparent and should not be confused with a fully historical sentiment-trained model.
