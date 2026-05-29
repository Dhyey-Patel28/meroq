# Sentiment system

Meroq supports a local-first sentiment architecture.

## Engines

- Lightweight financial lexicon
- `ProsusAI/finbert`
- `yiyanghkust/finbert-tone`
- `mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis`
- Finance sentiment ensemble

## Local model behavior

Hugging Face models are loaded through `transformers` and cached locally after the first download. No Hugging Face inference API is used by the app.

## Ensemble logic

The ensemble averages positive, neutral, and negative probabilities across available finance models. If a model cannot load, Meroq skips it. If no Hugging Face model can load, the lightweight fallback is used.

## Current limitation

Sentiment is currently contextual. It is shown in the dashboard but is not yet persisted as a historical feature for model training. The next research milestone is to align historical sentiment with returns and compare models with and without sentiment features.
