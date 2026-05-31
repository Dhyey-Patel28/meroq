# Human-Centered UX Principles

Meroq is a research tool, but the primary interface should behave like a product. The user should not need to understand model internals before reading the output.

## Product rules

1. **Conclusion first**: start with current price, forecast range, signal, and confidence. Keep diagnostics behind advanced sections.
2. **Trust before intensity**: every prediction should expose why confidence is low, moderate, or higher.
3. **Original sources matter**: news sentiment is only useful when the user can inspect the source article.
4. **Progressive disclosure**: show simple summaries by default and keep formulas, raw tables, and internals in detail views.
5. **No black boxes**: if sentiment changes the signal, show the adjustment; if a provider falls back, say so plainly.

## UX priorities

- First screen: readable in under 10 seconds.
- Prediction page: answer “what is the current outlook?”
- News page: answer “what sources influenced this sentiment?”
- Watchlist page: answer “what should I inspect next?”
- Portfolio page: answer “where is the risk concentrated?”

## Future direction

A dedicated frontend can use richer interactions, including a D3-based visual layer, after the API contract stabilizes.
