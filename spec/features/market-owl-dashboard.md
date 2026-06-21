---
status: approved
current_phase: plan
next_phase: review_then_test
next_skill: /sdd-test (after user review and approval)
---

# Feature Spec: Market Owl Dashboard (Existing System)

**Date:** 2026-04-04
**Status:** Approved (documents existing, live system)

## Overview

Market Owl is a quantitative macro regime analysis dashboard that identifies which of four economic seasons (Reflation, Overheat, Stagflation, Deflation) the market is currently in. It fetches data daily from FRED and Yahoo Finance, calculates normalized composite indices, and visualizes them via an interactive single-page web app hosted on GitHub Pages.

## Background & Motivation

Post-2022 market collapse demonstrated that traditional 60/40 portfolio allocation no longer provides reliable downside protection. Modern markets are macro-driven — broad regime shifts (Fed policy, inflation cycles, liquidity flows) swamp individual stock fundamentals. Market Owl was built to give individual investors the same macro regime awareness that institutional traders use to rotate assets dynamically.

The name "Market Owl" reflects the goal: wise, patient observation of macro signals rather than reactive noise-trading.

## Goals

- Identify the current macro regime quadrant (Growth vs Inflation axes) in real time
- Surface 5 composite indices: Growth, Inflation, Liquidity, Sentiment, Leading
- Automate daily data refresh with no manual intervention
- Provide educational context explaining what each signal means and why it matters
- Be fast, mobile-friendly, and dependency-minimal

## Non-Goals (Out of Scope)

- Portfolio tracking or trade execution
- Real-time (intraday) data
- User accounts or personalization
- Stock-specific or earnings analysis
- Server-side rendering

## User Stories

- As an investor, I want to know which macro regime we're in so I can tilt my allocation accordingly
- As an investor, I want to see the trend of Growth and Inflation indices over time so I can detect regime transitions early
- As a curious reader, I want to understand the methodology behind each chart so I can evaluate its credibility
- As a returning user, I want the data to be updated automatically so I don't have to refresh manually

## Functional Requirements

- FR-01: Display a scatter plot mapping current (Growth, Inflation) coordinates onto four regime quadrants
- FR-02: Display time-series line charts for all 5 composite indices
- FR-03: Display time-series charts for all 12 component sub-indicators
- FR-04: Each chart must have a modal info button explaining what it measures and how
- FR-05: Data must update automatically every day via GitHub Actions cron
- FR-06: Navigation between Dashboard (`/`), About (`/about`), and References (`/references`) must work without page reload
- FR-07: Layout must be responsive (4-col desktop → 2-col tablet → 1-col mobile)

## Non-Functional Requirements

- **Performance:** Page load under 2s on desktop; JSON data payload kept minimal via compact array format
- **Reliability:** GitHub Actions cron with `[skip ci]` tag to prevent recursive builds
- **Maintainability:** Source files in `src/` compiled to minified production files; config in `.minify.json`
- **SEO:** Full OpenGraph, Twitter Card, JSON-LD schema.org markup present
- **Accessibility:** Semantic HTML, color-coded by indicator family, readable contrast

## Technical Design

### Approach

Static site on GitHub Pages with a Python-powered daily data pipeline running in CI. No server, no database — data lives as a JSON file committed to the repository.

### Architecture

```
Browser
  └─ index.html (entry)
      ├─ Chart.js (CDN)
      └─ index.min.js
          ├─ fetch('/data/market_indices.json') — loads all historical data
          ├─ createCharts() — initializes 16 Chart.js instances
          ├─ handleLocation() — SPA routing via history.pushState
          └─ Modal system — info popups per chart

GitHub Actions (daily cron 00:00 UTC)
  └─ update_indices.py
      ├─ fredapi → FRED data (PMI, inflation expectations, yields, liquidity)
      ├─ yfinance → ETF & commodity data
      ├─ pandas → Z-score normalization (252-day rolling window)
      └─ Writes data/market_indices.json → commits → pushes
```

### Key Calculations

| Indicator | Source Data | Method |
|-----------|------------|--------|
| Growth Index | PMI (IPMAN) + XLY/XLP ratio | Z-score avg |
| Inflation Index | T5YIFR momentum + DBC RoC | Z-score avg |
| Liquidity Index | WALCL − TGA − RRP | Raw USD value |
| Sentiment Index | SPY momentum, VIX, TLT/SPY return, BAMLH0A0HYM2 | Scored 0–100, avg |
| Leading Indicator | Copper/Gold (HG=F/GC=F), SPHB/SPLV, DGS10−DGS2 | Z-score avg |

### Data Storage

`/data/market_indices.json` — compact array-of-arrays, one row per trading day:
```
[date, growth, inflation, liquidity, sentiment, leading,
 z_pmi, z_ratio, z_t5yifr, z_commodity, net_liquidity_raw,
 score_momentum, score_vix, score_safehaven, score_junk,
 z_coppergold, z_betavol, z_yieldspread]
```

### File Structure

```
/
├─ index.html           # Production entry (minified)
├─ index.min.js         # Production JS (minified)
├─ index.css            # Production CSS (minified)
├─ 404.html             # Copy of index.html for SPA routing on GitHub Pages
├─ src/
│   ├─ index.html       # Source HTML
│   ├─ index.js         # Source JS
│   └─ index.css        # Source CSS
├─ data/
│   └─ market_indices.json
├─ scripts/
│   └─ update_indices.py
├─ .github/workflows/
│   └─ weekly_update.yml
├─ .agent/workflows/
│   └─ deploy.md
├─ .minify.json
├─ CNAME                # marketowl.net
├─ robots.txt
└─ sitemap.xml
```

## Affected Areas

All current code is part of this spec. No pre-existing system was modified to create it.

## Test Strategy

- **Manual:** Visual check of charts after daily data update
- **Data integrity:** `update_indices.py` should validate that all expected columns are present before writing
- **Regression:** Check that minification doesn't break chart rendering or SPA routing
- **Responsive:** Test at 375px, 768px, 1200px, 1440px viewports

## Rollout Considerations

- Fully live at marketowl.net — all changes are deployed immediately on push to main
- Breaking changes to `market_indices.json` schema require coordinated update of both `update_indices.py` and `index.js`

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| FRED API key expiry or rate limit | Store as GitHub secret; monitor Action logs |
| Yahoo Finance API breaking change | Pin `yfinance` version; monitor `requirements.txt` |
| JSON schema mismatch between pipeline and frontend | Add column-count assertion in `update_indices.py` |
| `score_putcall` field appears legacy/unused | Resolved (Phase 1, T1.1): confirmed dead — hardcoded placeholder, never rendered (chart call was commented out, no DOM element existed). Removed from JSON schema, `update_indices.py`, `src/index.js`, and migrated out of `data/market_indices.json`'s existing 49 rows. |
| GitHub Actions cron delay causing stale data | Acceptable — data is daily, not real-time |

## Open Questions

- ~~Is `score_putcall` still calculated and sourced? If not, it should be removed from the JSON schema and frontend parsing~~ Resolved in Phase 1 (T1.1): removed entirely.
- Should the Liquidity Index be normalized (Z-scored) for better comparability with other indices?
- Is there a plan for a regime history timeline showing past quadrant positions?
