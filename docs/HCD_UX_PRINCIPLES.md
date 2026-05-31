# Human-Centered UX Principles

Meroq should not feel like a model dump. It should help a user answer a clear question:

> What is the current read, how much should I trust it, and what evidence can I inspect?

## Product rules

1. **Conclusion first**
   - Show the signal, probability, confidence, and risk lens before technical artifacts.

2. **Evidence second**
   - News sentiment must show source links so a user can open the original article.

3. **Advanced details are optional**
   - Tables, raw feature values, diagnostics, and model internals belong behind disclosure.

4. **Plain-English labels**
   - Use phrases such as "balanced", "constructive", "high downside risk", and "source-backed sentiment".
   - Keep numeric values visible, but pair them with interpretation.

5. **Do not overstate certainty**
   - Meroq is a research system. Forecasts and sentiment are directional lenses, not instructions.

## Current 1.8.1 implementation

- Frontend ticker analysis shows a clear signal and plain-English read.
- Recent headlines are rendered as article cards with source links.
- URL fields in tables are clickable.
- The dashboard explains the local FastAPI + Next.js workflow without sounding like an internal scaffold.
