# Stage 5 NLP Sentiment Plan

Stage 5 will add financial news sentiment to Meroq.

## Goal

Add sentiment as both a user-facing insight and a model feature.

The product should answer:

```text
What is the recent news tone around this stock?
Is sentiment positive, neutral, or negative?
Does sentiment improve prediction quality?
```

## Planned Features

### 1. News Ingestion

Fetch recent company news for the selected ticker.

Candidate APIs:

- Finnhub
- NewsAPI
- Alpha Vantage news sentiment
- Polygon news
- SEC filings later

Start with one API to keep the implementation simple.

### 2. Sentiment Model

Use FinBERT for financial text sentiment.

Output per headline:

- Positive probability
- Neutral probability
- Negative probability
- Final sentiment label
- Sentiment score

### 3. Sentiment Tab

Add a new Results tab:

```text
Sentiment
```

Show:

- Recent headlines
- Source/date
- Sentiment label
- Sentiment score
- Positive/neutral/negative count
- Sentiment trend over time

### 4. Sentiment Features

Create daily features:

- `sentiment_mean`
- `sentiment_count`
- `positive_ratio`
- `negative_ratio`
- `sentiment_momentum`
- `news_volume_change`

### 5. Model Comparison With Sentiment

Compare:

- Technical-only model
- Technical + sentiment model

This is important because sentiment should prove that it adds value.

### 6. Storage

Save news and sentiment locally.

Suggested SQLite tables:

```text
news_articles
sentiment_scores
daily_sentiment_features
```

### 7. Configuration

Use environment variables or Streamlit secrets for API keys.

Never commit API keys.

Files to add later:

```text
.env.example
src/news_loader.py
src/sentiment.py
src/sentiment_features.py
```

## Stage 5 Success Criteria

Stage 5 is complete when:

- User can run sentiment analysis for a ticker
- App shows recent headlines and sentiment labels
- Daily sentiment features are built
- At least one model can train with sentiment features
- Model comparison shows technical-only vs technical+sentiment performance
- API keys are documented but not committed
