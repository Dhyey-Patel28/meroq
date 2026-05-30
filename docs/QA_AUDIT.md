# QA Audit

This document captures a senior tester pass over Meroq after the portfolio-risk release. The goal was to review the app as a first-time user, identify confusing behavior, and document the fixes applied in release 1.2.1.

## Summary

Meroq has strong analytical depth, but several parts of the user experience were becoming too research-oriented for a product-style dashboard. The main issue was not model correctness; it was predictability and clarity. A user should understand what mode they are running, why it may be slow, and which sections are optional diagnostics.

## Findings and Fixes

| ID | Severity | Area | Finding | Fix in 1.2.1 |
|---|---|---|---|---|
| QA-001 | High | Analysis mode | Fast, Research, and Full modes could still use stale Streamlit widget state from earlier manual choices. Example: Full mode could show Stacking Ensemble even when the preset intended XGBoost. | Non-Custom modes now enforce preset model, comparison set, and walk-forward settings. Manual controls are only available in Custom mode. |
| QA-002 | High | Performance | Users could accidentally combine Finance Sentiment Ensemble, Full Analysis, Advanced All models, walk-forward comparison, and large headline counts. This makes the app feel frozen on local CPU. | Added clearer warnings for ensemble sentiment with many headlines and made presets more deterministic. The recommended path remains Fast mode first. |
| QA-003 | Medium | Sidebar UX | The sidebar exposed too many advanced knobs for normal use. This made it hard to know which controls mattered. | Manual model/backtest controls are hidden behind Custom mode. Preset modes show read-only configuration summaries instead. |
| QA-004 | Medium | Report UX | The Report tab opened a large Markdown preview by default, which made the product feel noisy after a run. | Report preview is collapsed by default. Downloads remain available without forcing the user to scroll through the full report. |
| QA-005 | Medium | First-run guidance | The idle state gave minimal instruction and did not explain a good workflow. | The initial state now recommends Fast mode and explains a simple workflow: Prediction, News Sentiment, Risk Simulation, then Watchlist/Portfolio if needed. |
| QA-006 | Medium | News relevance | Broad NewsAPI searches can return unrelated headlines for ambiguous tickers such as PLAY. | Already fixed in 1.0.1 with ticker-to-company resolution, company aliases, NewsAPI query generation, and relevance filtering. Kept as a regression item. |
| QA-007 | Low | Release hygiene | Uploaded project archives sometimes included generated SQLite databases and `__pycache__` files. | The 1.2.1 package excludes local databases and Python cache files. |
| QA-008 | Low | Advanced diagnostics | Model Details, Data Manager, Sentiment Modeling, and Walk-forward Backtest are useful but not first-read product content. | Kept these sections available, but the main workflow and waiting copy now guide users toward core product tabs first. |

## Recommended User Workflow

1. Start with **Fast mode**.
2. Run one ticker with `5y` and `1d`.
3. Review **Prediction**, **News Sentiment**, and **Risk Simulation**.
4. Enable **Watchlist scan** only when you want cross-ticker idea discovery.
5. Enable **Portfolio view** only after a watchlist scan.
6. Use **Research mode** or **Full analysis mode** only when you intentionally want slower model diagnostics.
7. Use **Custom** only when manually tuning models and walk-forward settings.

## Regression Checklist

Before each release, verify:

- Fast mode uses XGBoost and does not accidentally inherit a stale ensemble model.
- Research mode enables only the selected-model walk-forward backtest.
- Full analysis mode enables advanced comparison intentionally and displays a slow-run warning.
- Custom mode exposes all manual controls.
- Report downloads do not rerun or erase the current analysis.
- Ambiguous tickers such as `PLAY` use company-aware news matching.
- `.env`, SQLite databases, and cache files are not committed or packaged.

## Remaining Product Opportunities

These are not blockers for 1.2.1 but should be considered later:

- Add a compact landing page or guided onboarding panel.
- Add saved user presets such as “Quick daily check” and “Research run.”
- Add a true backend API layer so Streamlit is not responsible for both orchestration and presentation.
- Add dedicated UI tests once the dashboard stabilizes.
