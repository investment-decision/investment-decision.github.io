---
phase: clarify
project_type: brownfield
feature_name: market-regime-indicator-refinement
status: complete
current_phase: clarify
next_phase: research
next_skill: /sdd-research
---

# SDD Context: Market Regime Indicator Refinement

**Project:** Market Owl (marketowl.net)
**Date:** 2026-04-05
**Type:** Brownfield — refining a specific component of an existing system

## Problem Statement

The Market Owl dashboard's market regime indicator produces wrong historical calls and feels incorrectly weighted. Key failures include missed or delayed signals during the 2020 crash, 2022 stagflation shift, and 2023 recovery. The composite index weighting (Growth, Inflation, Liquidity, Sentiment, Leading) does not reflect relative predictive importance. This undermines investor confidence in using the indicator for actual ETF allocation decisions.

## Success Criteria

1. **Backtested accuracy** — Correct regime calls during three benchmark periods:
   - 2020 COVID crash and recovery
   - 2022 stagflation (inflation spike + growth slowdown)
   - 2023 soft landing / recovery
2. **Timely signals** — Regime transitions align within 2–4 weeks of consensus macro narrative
3. **All of "most trusted"** — Academically grounded, transparent in reasoning, low noise, backtested

## Scope

### In Scope
- Composite index weighting (Growth, Inflation, Liquidity, Sentiment, Leading) — recalibrate relative weights
- Regime detection algorithm — improve quadrant classification logic
- New free data sources — FRED, Yahoo Finance, or other free APIs to strengthen signal quality
- Visual presentation — how regimes are displayed on the dashboard
- ETF allocation recommendations per regime — refine or add per-regime asset allocation guidance

### Out of Scope
- Paid/premium data sources
- Server-side logic or databases
- Framework changes (no React, Vue, etc.)
- Real-time / intraday data

## Users & Context

- Solo developer / investor (primary user) building for personal use and public audience
- Audience: macro-aware investors who want data-driven regime identification for index ETF allocation
- Usage pattern: daily check-in, regime-driven rebalancing decisions

## Technical Constraints & Preferences

- **Hosting:** GitHub Pages (static only — no server-side code)
- **Data pipeline:** Python 3.11, pandas, yfinance, fredapi — must remain Python-based
- **Frontend:** Vanilla HTML5/CSS3/JS (ES6+), Chart.js — no new frameworks
- **CI/CD:** GitHub Actions daily cron (00:00 UTC / 9 AM KST)
- **Data sources:** FRED API + Yahoo Finance already integrated; open to any additional free APIs
- **Build:** Terser + CleanCSS + HTMLMinifier for production

## Dependencies

- FRED API (via `fredapi` Python library) — requires GitHub secret `FRED_API_KEY`
- Yahoo Finance (via `yfinance`) — free, no key required
- Chart.js via CDN
- GitHub Actions for daily data refresh

## Known Risks & Unknowns

- **Overfitting risk** — recalibrating weights on historical data may not generalize to future regimes
- **Data availability** — some ideal indicators may not be available via free APIs with sufficient history
- **Lag inherent in macro data** — FRED data often revised; some series have 1–4 week publication lag
- **Regime ambiguity** — real markets spend time in transition; any 4-quadrant model has edge cases

## Open Questions

- Which specific historical regime calls were wrong? (needs backtest analysis in research phase)
- Are there published academic frameworks (e.g., Bridgewater All Weather, Fidelity sector rotation) that can anchor the weighting methodology?
- What free data sources beyond FRED/Yahoo Finance have sufficient history (10+ years) for backtesting?

---

## Summary for Next Phase

The Market Owl regime indicator needs to be refactored to produce more accurate, trustworthy macro regime signals for index ETF investment decisions. Key problems are wrong historical calls and mis-weighted composite indices. Research should identify: (1) academically-grounded weighting methodologies for Growth/Inflation/Liquidity composites, (2) additional free data sources that improve signal quality, and (3) improved regime detection algorithms — all within the constraint of a static GitHub Pages site with a Python data pipeline and vanilla JS frontend.
