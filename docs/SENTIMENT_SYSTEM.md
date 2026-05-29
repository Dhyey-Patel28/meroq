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
